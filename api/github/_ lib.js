
import crypto from "node:crypto";

const GITHUB_API = "https://api.github.com";

export function authorize(req, res) {
  const apiKey = process.env.GITHUB_API_KEY;
  const providedKey = req.headers["x-api-key"];

  if (!apiKey) {
    res.status(500).json({ error: "GITHUB_API_KEY is not configured" });
    return false;
  }

  if (
    typeof providedKey !== "string" ||
    providedKey.length !== apiKey.length ||
    !crypto.timingSafeEqual(
      Buffer.from(providedKey),
      Buffer.from(apiKey)
    )
  ) {
    res.status(401).json({ error: "Unauthorized" });
    return false;
  }

  return true;
}

export function validPath(path) {
  if (typeof path !== "string" || path.length === 0 || path.length > 500) {
    return false;
  }

  if (path.startsWith("/") || path.includes("\\")) {
    return false;
  }

  const parts = path.split("/");

  return parts.every(
    (part) =>
      part.length > 0 &&
      part !== "." &&
      part !== ".." &&
      !/[\x00-\x1F\x7F]/.test(part)
  );
}

export function repoPath(path) {
  return path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/");
}

export async function github(endpoint, options = {}) {
  const token = process.env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("GITHUB_TOKEN is not configured");
  }

  const response = await fetch(`${GITHUB_API}${endpoint}`, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const text = await response.text();
  let data = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { message: text };
  }

  if (!response.ok) {
    const error = new Error(
      data?.message || `GitHub API error: ${response.status}`
    );
    error.status = response.status;
    throw error;
  }

  return data;
}

export function getRepoPath(path) {
  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;

  if (!owner || !repo) {
    throw new Error("GITHUB_OWNER or GITHUB_REPO is not configured");
  }

  return `/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${repoPath(path)}`;
}

export function fail(res, error) {
  const status = error.status || 500;

  return res.status(status).json({
    error: error.message || "Internal server error",
  });
}
