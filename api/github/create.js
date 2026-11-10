
import {
  authorize,
  github,
  getRepoPath,
  validPath,
  fail,
} from "./_lib.js";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!authorize(req, res)) return;

  try {
    const { path, content, confirm } = req.body || {};

    if (!validPath(path)) {
      return res.status(400).json({ error: "Invalid file path" });
    }

    if (typeof content !== "string" || content.length > 500000) {
      return res.status(400).json({
        error: "Invalid content or file too large",
      });
    }

    if (confirm !== true) {
      return res.status(400).json({
        error: "Confirmation required",
      });
    }

    const result = await github(getRepoPath(path), {
      method: "PUT",
      body: JSON.stringify({
        message: `Vex GPT: create ${path}`,
        content: Buffer.from(content, "utf8").toString("base64"),
        branch: process.env.GITHUB_BRANCH || "master",
      }),
    });

    return res.status(201).json({
      success: true,
      path: result.content.path,
      sha: result.content.sha,
      message: "File created successfully",
    });
  } catch (error) {
    return fail(res, error);
  }
}
