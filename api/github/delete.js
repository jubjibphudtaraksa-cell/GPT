
import {
  authorize,
  github,
  getRepoPath,
  validPath,
  fail,
} from "./_lib.js";

export default async function handler(req, res) {
  if (req.method !== "DELETE") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!authorize(req, res)) return;

  try {
    const { path, sha, confirm } = req.body || {};

    if (!validPath(path)) {
      return res.status(400).json({ error: "Invalid file path" });
    }

    if (typeof sha !== "string" || !sha) {
      return res.status(400).json({
        error: "Current file SHA is required",
      });
    }

    if (confirm !== true) {
      return res.status(400).json({
        error: "Confirmation required",
      });
    }

    const result = await github(getRepoPath(path), {
      method: "DELETE",
      body: JSON.stringify({
        message: `Vex GPT: delete ${path}`,
        sha,
        branch: process.env.GITHUB_BRANCH || "master",
      }),
    });

    return res.status(200).json({
      success: true,
      path,
      commit: result.commit.sha,
      message: "File deleted successfully",
    });
  } catch (error) {
    return fail(res, error);
  }
}
