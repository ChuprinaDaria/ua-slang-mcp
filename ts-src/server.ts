#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { readFileSync, existsSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

// Resolve data directory — works both from dist/ and ts-src/
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = join(__dirname, "..", "data");

// --- Data loading ---

interface SlangEntry {
  id: string;
  word: string;
  meaning: string;
  example: string;
  first_seen: string;
  last_seen: string;
  frequency_score: number;
  frequency_trend: string;
  category: string;
  tags: string[];
  status: string;
}

interface StreakEntry {
  id: string;
  phrase: string;
  meaning: string;
  context: string;
  example: string;
  first_seen: string;
  source_count: number;
  category: string;
  tags: string[];
  status: string;
}

interface MemeEntry {
  id: string;
  title: string;
  format: string;
  description: string;
  example: string;
  template: string;
  first_seen: string;
  last_seen: string;
  frequency_score: number;
  frequency_trend: string;
  lifecycle_stage: string;
  virality_score: number;
  category: string;
  tags: string[];
  status: string;
}

function loadJson<T>(filename: string): T[] {
  const path = join(DATA_DIR, filename);
  if (!existsSync(path)) return [];
  return JSON.parse(readFileSync(path, "utf-8"));
}

function daysSince(dateStr: string): number {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    return Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return -1;
  }
}

function freshnessLabel(days: number): string {
  if (days < 0) return "unknown";
  if (days <= 1) return "today";
  if (days <= 7) return "this_week";
  if (days <= 30) return "this_month";
  if (days <= 90) return "recent";
  return "stale";
}

function datasetMeta() {
  const packagesDir = join(DATA_DIR, "packages");
  let lastUpdate = "unknown";
  if (existsSync(packagesDir)) {
    const files = readdirSync(packagesDir)
      .filter((f: string) => f.endsWith(".json"))
      .sort()
      .reverse();
    if (files.length > 0) lastUpdate = files[0].replace(".json", "");
  }
  return {
    _dataset_last_updated: lastUpdate,
    _dataset_checked_at: new Date().toISOString(),
  };
}

function enrichItem<T extends { last_seen?: string; first_seen?: string }>(item: T): T & { _days_since_seen?: number; _freshness?: string } {
  const lastSeen = item.last_seen || item.first_seen || "";
  if (lastSeen) {
    const days = daysSince(lastSeen);
    return { ...item, _days_since_seen: days, _freshness: freshnessLabel(days) };
  }
  return item;
}

function withMeta(response: unknown[] | Record<string, unknown>) {
  const meta = datasetMeta();
  if (Array.isArray(response)) {
    return { ...meta, count: response.length, items: response };
  }
  return { ...meta, ...response };
}

// --- MCP Server ---

const server = new McpServer({
  name: "UA Slang",
  version: "0.1.0",
});

server.tool(
  "get_dataset_info",
  "Dataset size, last update date, coverage. Call this first to understand data freshness.",
  {},
  async () => {
    const slang = loadJson<SlangEntry>("slang.json");
    const streaks = loadJson<StreakEntry>("streaks.json");
    const memes = loadJson<MemeEntry>("memes_active.json");
    const activeSlang = slang.filter((s) => s.status === "active");
    const activeMemes = memes.filter((m) => m.status === "active");

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            withMeta({
              total_entries: slang.length + streaks.length + memes.length,
              slang_active: activeSlang.length,
              slang_deprecated: slang.length - activeSlang.length,
              streaks: streaks.length,
              memes_active: activeMemes.length,
              memes_dead: memes.length - activeMemes.length,
              source: "Threads (threads.net)",
              language: "Ukrainian internet language (slang + surzhyk + memes)",
              update_frequency: "daily",
              usage_hint:
                "Always call check_freshness() before using slang/memes in content. Streaks are always safe.",
            }),
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "search_slang",
  "Search slang by word or meaning. Each result includes _freshness (today/this_week/this_month/stale).",
  { query: z.string().describe("Word or meaning to search for"), only_active: z.boolean().default(true) },
  async ({ query, only_active }) => {
    const q = query.toLowerCase();
    const results = loadJson<SlangEntry>("slang.json")
      .filter((item) => {
        if (only_active && item.status !== "active") return false;
        return item.word.toLowerCase().includes(q) || item.meaning.toLowerCase().includes(q);
      })
      .map(enrichItem);

    return { content: [{ type: "text" as const, text: JSON.stringify(withMeta(results), null, 2) }] };
  }
);

server.tool(
  "search_streaks",
  "Search stable expressions/phrases. Streaks are always relevant — safe to use without freshness check.",
  { query: z.string().describe("Phrase or part to search for") },
  async ({ query }) => {
    const q = query.toLowerCase();
    const results = loadJson<StreakEntry>("streaks.json").filter(
      (item) =>
        item.phrase.toLowerCase().includes(q) ||
        item.meaning.toLowerCase().includes(q) ||
        (item.context || "").toLowerCase().includes(q)
    );

    return { content: [{ type: "text" as const, text: JSON.stringify(withMeta(results), null, 2) }] };
  }
);

server.tool(
  "get_trending_memes",
  "Top memes by virality_score. Includes _freshness — only use fresh memes for content.",
  { limit: z.number().default(10).describe("Number of memes (default: 10)") },
  async ({ limit }) => {
    const memes = loadJson<MemeEntry>("memes_active.json")
      .sort((a, b) => (b.virality_score || 0) - (a.virality_score || 0))
      .slice(0, limit)
      .map(enrichItem);

    return { content: [{ type: "text" as const, text: JSON.stringify(withMeta(memes), null, 2) }] };
  }
);

server.tool(
  "get_trending_slang",
  "Rising slang (frequency_trend = rising). If none rising — top by frequency_score.",
  { limit: z.number().default(10) },
  async ({ limit }) => {
    const slang = loadJson<SlangEntry>("slang.json");
    let result = slang.filter((s) => s.frequency_trend === "rising");
    if (result.length === 0) {
      result = [...slang].sort((a, b) => (b.frequency_score || 0) - (a.frequency_score || 0)).slice(0, limit);
    } else {
      result = result.slice(0, limit);
    }

    return { content: [{ type: "text" as const, text: JSON.stringify(withMeta(result.map(enrichItem)), null, 2) }] };
  }
);

server.tool(
  "suggest_for_post",
  "Suggest slang, streaks, and memes for a specific post topic. Returns only fresh and relevant items.",
  {
    topic: z.string().describe("Post topic (e.g. 'coffee', 'work', 'relationships')"),
    style: z.enum(["casual", "professional", "ironic"]).default("casual"),
  },
  async ({ topic, style }) => {
    const q = topic.toLowerCase();

    const slang = loadJson<SlangEntry>("slang.json")
      .filter((item) => {
        if (item.status !== "active") return false;
        const s = `${item.word} ${item.meaning} ${item.example}`.toLowerCase();
        return s.includes(q);
      })
      .slice(0, 5)
      .map(enrichItem);

    const streaks = loadJson<StreakEntry>("streaks.json")
      .filter((item) => {
        const s = `${item.phrase} ${item.meaning} ${item.context}`.toLowerCase();
        return s.includes(q);
      })
      .slice(0, 5);

    const memes = loadJson<MemeEntry>("memes_active.json")
      .filter((item) => {
        if (item.status !== "active") return false;
        const s = `${item.title} ${item.description} ${item.example}`.toLowerCase();
        return s.includes(q);
      })
      .slice(0, 3)
      .map(enrichItem);

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            withMeta({ topic, style, slang, streaks, memes, tip: "Use only items with _freshness = today/this_week for current content" }),
            null,
            2
          ),
        },
      ],
    };
  }
);

server.tool(
  "check_freshness",
  "Check if a word/meme is still relevant. MUST call before using any slang/meme in content.",
  { word: z.string().describe("Word or phrase to check") },
  async ({ word }) => {
    const q = word.toLowerCase();

    for (const item of loadJson<SlangEntry>("slang.json")) {
      if (item.word.toLowerCase().includes(q)) {
        const days = daysSince(item.last_seen || "");
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                withMeta({
                  word: item.word,
                  status: item.status,
                  frequency_score: item.frequency_score,
                  frequency_trend: item.frequency_trend,
                  last_seen: item.last_seen || "unknown",
                  _days_since_seen: days,
                  _freshness: freshnessLabel(days),
                  is_fresh: item.status === "active" && item.frequency_score >= 4,
                  verdict: item.status === "active" && item.frequency_score >= 4 ? "safe to use" : "outdated or rare — avoid",
                }),
                null,
                2
              ),
            },
          ],
        };
      }
    }

    for (const item of loadJson<MemeEntry>("memes_active.json")) {
      if (item.title.toLowerCase().includes(q)) {
        const days = daysSince(item.last_seen || "");
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(
                withMeta({
                  word: item.title,
                  status: item.status,
                  lifecycle_stage: item.lifecycle_stage,
                  virality_score: item.virality_score,
                  last_seen: item.last_seen || "unknown",
                  _days_since_seen: days,
                  _freshness: freshnessLabel(days),
                  is_fresh: item.status === "active",
                  verdict: item.status === "active" ? "safe to use" : "dead meme — don't use",
                }),
                null,
                2
              ),
            },
          ],
        };
      }
    }

    return {
      content: [
        { type: "text" as const, text: JSON.stringify(withMeta({ word, status: "not_found", is_fresh: false, verdict: "not in database" }), null, 2) },
      ],
    };
  }
);

server.tool(
  "get_daily_package",
  "Get daily update package. Contains stats: how many new, how many deprecated.",
  { package_date: z.string().default("").describe("Date YYYY-MM-DD (default: latest)") },
  async ({ package_date }) => {
    const packagesDir = join(DATA_DIR, "packages");
    if (!existsSync(packagesDir)) {
      return { content: [{ type: "text" as const, text: JSON.stringify({ error: "no packages available" }) }] };
    }

    const files: string[] = readdirSync(packagesDir).filter((f: string) => f.endsWith(".json")).sort().reverse();

    let targetFile: string;
    if (package_date) {
      targetFile = `${package_date}.json`;
      if (!files.includes(targetFile)) {
        return { content: [{ type: "text" as const, text: JSON.stringify({ error: `package for ${package_date} not found` }) }] };
      }
    } else {
      if (files.length === 0) {
        return { content: [{ type: "text" as const, text: JSON.stringify({ error: "no packages available" }) }] };
      }
      targetFile = files[0];
    }

    const data = JSON.parse(readFileSync(join(packagesDir, targetFile), "utf-8"));
    return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
  }
);

server.tool("get_all_slang", "All active slang with dates and _freshness.", { category: z.string().default("") }, async ({ category }) => {
  let slang = loadJson<SlangEntry>("slang.json").filter((s) => s.status === "active");
  if (category) {
    slang = slang.filter((s) => s.tags.join(" ").toLowerCase().includes(category.toLowerCase()));
  }
  return { content: [{ type: "text" as const, text: JSON.stringify(withMeta(slang.map(enrichItem)), null, 2) }] };
});

server.tool("get_all_streaks", "All stable expressions. Streaks are always safe to use.", {}, async () => {
  return { content: [{ type: "text" as const, text: JSON.stringify(withMeta(loadJson<StreakEntry>("streaks.json")), null, 2) }] };
});

// --- Start ---

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(console.error);
