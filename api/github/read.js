
import {
  authorize,
  github,
  getRepoPath,
  validPath,
  fail,
} from "./_lib.js";

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!authorize(req, res)) return;

  try {
    const path = req.query.path;

    if (!validPath(path)) {
      return res.status(400).json({
        error: "Invalid file path",
      });
    }

    const data = await github(getRepoPath(path));

    if (Array.isArray(data)) {
      return res.status(400).json({
        error: "Path is a directory, not a file",
      });
    }

    if (data.type !== "file" || !data.content) {
      return res.status(400).json({
        error: "Unsupported file or empty content",
      });
    }

    const content = Buffer.from(
      data.content,
      "base64"
    ).toString("utf8");

    return res.status(200).json({
      success: true,
      path: data.path,
      sha: data.sha,
      size: data.size,
      content,
    });
  } catch (error) {
    return fail(res, error);
  }
}
