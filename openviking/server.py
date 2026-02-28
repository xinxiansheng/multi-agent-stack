#!/usr/bin/env python3
"""
OpenViking MCP Server — Knowledge Base Access
==============================================
Exposes RAG query, semantic search, resource indexing,
and session memory commit via MCP protocol.

Tools:
  - query: RAG Q&A with retrieved context
  - search: Fast semantic search
  - smart_search: Intent analysis + hierarchical retrieval
  - add_resource: Index new file/directory/URL
  - session_commit: Extract memories from conversation

Runs on HTTP at port 2033 (configurable via OPENVIKING_PORT env).
"""

import json
import os
import sys
from pathlib import Path

# Disable proxy for local Volcengine calls
os.environ["NO_PROXY"] = "*"

try:
    import openviking as ov
    from openviking_cli.utils.config.open_viking_config import OpenVikingConfig
except ImportError:
    print("ERROR: openviking not installed. Run: pip install openviking")
    sys.exit(1)

try:
    from fastmcp import FastMCP
except ImportError:
    print("ERROR: fastmcp not installed. Run: pip install fastmcp")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────

OV_DATA = os.environ.get("OPENVIKING_DATA", os.path.expanduser("~/.openclaw/openviking-data"))
OV_CONF_FILE = os.environ.get("OPENVIKING_CONF", os.path.expanduser("~/.openviking/ov.conf"))
PORT = int(os.environ.get("OPENVIKING_PORT", "2033"))

# ── Initialize ─────────────────────────────────────────────────

with open(OV_CONF_FILE) as f:
    config = OpenVikingConfig.from_dict(json.load(f))

client = ov.SyncOpenViking(path=OV_DATA, config=config)
client.initialize()

mcp = FastMCP("OpenViking Knowledge Base")

# ── Tools ──────────────────────────────────────────────────────

@mcp.tool()
def query(question: str, top_k: int = 5) -> str:
    """RAG query: retrieve relevant context and generate answer."""
    try:
        result = client.query(question, top_k=top_k)
        return json.dumps({
            "answer": result.answer if hasattr(result, "answer") else str(result),
            "sources": [
                {"uri": r.uri, "score": round(r.score, 3)}
                for r in (result.resources if hasattr(result, "resources") else [])
            ][:top_k]
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search(query_text: str, top_k: int = 5) -> str:
    """Fast semantic search across all indexed resources."""
    try:
        results = client.search(query_text)
        return json.dumps({
            "results": [
                {"uri": r.uri, "score": round(r.score, 3), "snippet": r.text[:200] if hasattr(r, "text") else ""}
                for r in results.resources[:top_k]
            ]
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def smart_search(query_text: str) -> str:
    """Intent-aware hierarchical search: memories → resources → skills."""
    try:
        # Search memories first
        mem_results = client.search(query_text, collection="memories")
        # Then resources
        res_results = client.search(query_text, collection="resources")

        output = {"memories": [], "resources": []}
        if hasattr(mem_results, "resources"):
            output["memories"] = [
                {"uri": r.uri, "score": round(r.score, 3)}
                for r in mem_results.resources[:3]
            ]
        if hasattr(res_results, "resources"):
            output["resources"] = [
                {"uri": r.uri, "score": round(r.score, 3)}
                for r in res_results.resources[:5]
            ]
        return json.dumps(output, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_resource(resource_path: str) -> str:
    """Index a new file, directory, or URL into the knowledge base."""
    try:
        result = client.add_resource(path=resource_path)
        return json.dumps({
            "status": "ok",
            "uri": result.get("root_uri", resource_path) if isinstance(result, dict) else str(result)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def session_commit(messages_json: str) -> str:
    """
    Extract memories from a conversation session.
    Input: JSON array of {role, content} messages.
    Extracts: profile, preferences, entities, events, cases, patterns.
    """
    try:
        messages = json.loads(messages_json)
        result = client.session_commit(messages=messages)
        return json.dumps({
            "status": "ok",
            "extracted": result if isinstance(result, dict) else str(result)
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"OpenViking MCP Server starting on port {PORT}...")
    mcp.run(transport="http", host="0.0.0.0", port=PORT)
