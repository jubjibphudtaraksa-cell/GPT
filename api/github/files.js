
import { authorize, github, fail } from "./_lib.js";

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!authorize(req, res)) return;

  try {
    const owner = process.env.GITHUB_OWNER;
    const repo = process.env.GITHUB_REPO;
    const branch = process.env.GITHUB_BRANCH || "master";

    if (!owner || !repo) {
      return res.status(500).json({
        error: "GitHub repository settings are missing",
      });
    }

    const data = await github(
      `/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/git/trees/${encodeURIComponent(branch)}?recursive=1`
    );

    const files = (data.tree || [])
      .filter((item) => item.type === "blob")
      .map((item) => ({
        path: item.path,
        sha: item.sha,
        size: item.size,
      }));

    return res.status(200).json({
      success: true,
      branch,
      total: files.length,
      files,
    });
  } catch (error) {
    return fail(res, error);
  }
}
