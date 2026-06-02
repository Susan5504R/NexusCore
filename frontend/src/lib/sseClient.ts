import { GraphStreamEvent } from "./types";
import { API_BASE_URL } from "./config";

export async function* streamGraphRun(targetFile: string, logs: string[]): AsyncGenerator<GraphStreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/run/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "text/event-stream"
    },
    body: JSON.stringify({ target_file: targetFile, logs })
  });

  if (!response.ok) {
    throw new Error(`Failed to start stream: ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("No response body returned from server.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a double newline
    const parts = buffer.split("\n\n");
    // The last chunk might be incomplete, so we leave it in the buffer
    buffer = parts.pop() || ""; 

    for (const part of parts) {
      if (!part.trim()) continue;
      
      const lines = part.split("\n");
      let dataStr = "";

      for (const line of lines) {
        if (line.startsWith("data:")) {
          dataStr = line.slice(5).trim();
        }
      }

      if (dataStr) {
        try {
          const parsedData = JSON.parse(dataStr) as GraphStreamEvent;
          yield parsedData;
        } catch (e) {
          console.error("Failed to parse SSE data:", dataStr);
        }
      }
    }
  }
}
