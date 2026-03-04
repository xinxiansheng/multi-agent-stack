#!/usr/bin/env python3
"""
OpenViking MCP Server — Knowledge Base Access
==============================================
Exposes RAG query, semantic search, smart search, resource indexing,
and session memory commit via MCP protocol.

Tools:
  - query: RAG Q&A with retrieved context
  - search: Fast semantic search
  - smart_search: Intent analysis + hierarchical retrieval
  - add_resource: Index new file/directory/URL
  - session_commit: Extract memories from conversation

Usage:
  python server.py                              # HTTP on port 2033
  python server.py --port 2033 --host 127.0.0.1 # Custom host/port
  python server.py --transport stdio            # stdio for direct MCP
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

import openviking as ov
from openviking_cli.utils.config.open_viking_config import OpenVikingConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openviking-mcp")

# Global state
_recipe = None
_client: Optional[ov.SyncOpenViking] = None
_config_path: str = os.environ.get(
    "OV_CONFIG", os.path.expanduser("~/.openviking/ov.conf"))
_data_path: str = os.environ.get(
    "OV_DATA", os.path.expanduser("~/.openclaw/openviking-data"))

# Disable proxy for local Volcengine calls
os.environ["NO_PROXY"] = "*"


def _get_recipe():
    global _recipe
    if _recipe is None:
        try:
            from common.recipe import Recipe
            _recipe = Recipe(config_path=_config_path, data_path=_data_path)
        except ImportError:
            logger.warning("Recipe not available, query tool will use client")
    return _recipe


def _get_client() -> ov.SyncOpenViking:
    global _client
    if _client is None:
        with open(_config_path) as f:
            config_dict = json.load(f)
        config = OpenVikingConfig.from_dict(config_dict)
        _client = ov.SyncOpenViking(path=_data_path, config=config)
        _client.initialize()
    return _client


def create_server(host: str = "127.0.0.1", port: int = 2033) -> FastMCP:
    mcp = FastMCP(
        name="openviking-mcp",
        instructions=(
            "OpenViking MCP Server — knowledge base with RAG, "
            "semantic search, smart search, and session memory. "
            "Use 'smart_search' for best results, 'search' for fast lookup, "
            "'query' for RAG answers, 'session_commit' for memory extraction."
        ),
        host=host,
        port=port,
        stateless_http=True,
        json_response=True,
    )

    @mcp.tool()
    async def query(
        question: str,
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        score_threshold: float = 0.2,
        system_prompt: str = "",
    ) -> str:
        """RAG query: retrieve context and generate answer via LLM."""
        def _sync():
            recipe = _get_recipe()
            if recipe:
                return recipe.query(
                    user_query=question, search_top_k=top_k,
                    temperature=temperature, max_tokens=max_tokens,
                    score_threshold=score_threshold,
                    system_prompt=system_prompt or None,
                )
            # Fallback to basic search + return
            client = _get_client()
            results = client.search(question)
            items = []
            for r in (results.resources or [])[:top_k]:
                items.append(f"[{r.score:.3f}] {r.uri}")
            return {"answer": "\n".join(items) or "No results", "context": []}

        result = await asyncio.to_thread(_sync)
        output = result.get("answer", str(result))
        if result.get("context"):
            output += "\n\n---\nSources:\n"
            for i, ctx in enumerate(result["context"], 1):
                uri_parts = ctx["uri"].split("/")
                filename = uri_parts[-1] if uri_parts else ctx["uri"]
                output += f"  {i}. {filename} (score: {ctx['score']:.4f})\n"
        timings = result.get("timings", {})
        if timings:
            output += (
                f"\n[search: {timings.get('search_time', 0):.2f}s, "
                f"llm: {timings.get('llm_time', 0):.2f}s, "
                f"total: {timings.get('total_time', 0):.2f}s]")
        return output

    @mcp.tool()
    async def search(
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.2,
        target_uri: str = "",
    ) -> str:
        """Fast semantic search (no LLM). Quick lookup when you know what
        you're looking for."""
        def _sync():
            recipe = _get_recipe()
            if recipe:
                return recipe.search(
                    query=query, top_k=top_k,
                    score_threshold=score_threshold,
                    target_uri=target_uri or None)
            client = _get_client()
            results = client.search(query)
            items = []
            for r in (results.resources or [])[:top_k]:
                items.append({
                    "uri": r.uri,
                    "score": r.score,
                    "content": getattr(r, "abstract", "")[:500],
                })
            return items

        results = await asyncio.to_thread(_sync)
        if not results:
            return "No relevant results found."
        parts = []
        for i, r in enumerate(results, 1):
            if isinstance(r, dict):
                preview = r.get("content", "")[:500]
                parts.append(
                    f"[{i}] {r['uri']} "
                    f"(score: {r['score']:.4f})\n{preview}")
            else:
                parts.append(f"[{i}] {r}")
        return f"Found {len(results)} results:\n\n" + "\n\n".join(parts)

    @mcp.tool()
    async def smart_search(
        query: str,
        top_k: int = 8,
        score_threshold: float = 0.15,
        session_id: str = "",
    ) -> str:
        """Smart search with intent analysis and hierarchical retrieval.
        Searches memories, resources, and skills. Best for complex queries."""
        def _sync():
            client = _get_client()
            session = None
            if session_id:
                try:
                    session = client.session(session_id)
                except Exception:
                    pass
            return client.search(
                query=query,
                session=session,
                limit=top_k,
                score_threshold=score_threshold,
            )

        results = await asyncio.to_thread(_sync)
        parts = []

        if results.memories:
            parts.append(f"## Memories ({len(results.memories)})")
            for m in results.memories[:top_k]:
                abstract = getattr(m, 'abstract', '') or ''
                parts.append(
                    f"  [{m.score:.3f}] {m.uri}\n    {abstract[:200]}")

        if results.resources:
            parts.append(f"\n## Resources ({len(results.resources)})")
            for r in results.resources[:top_k]:
                abstract = getattr(r, 'abstract', '') or ''
                parts.append(
                    f"  [{r.score:.3f}] {r.uri}\n    {abstract[:200]}")

        if results.skills:
            parts.append(f"\n## Skills ({len(results.skills)})")
            for s in results.skills[:top_k]:
                abstract = getattr(s, 'abstract', '') or ''
                parts.append(
                    f"  [{s.score:.3f}] {s.uri}\n    {abstract[:200]}")

        if results.query_plan:
            reasoning = getattr(results.query_plan, 'reasoning', '') or ''
            if reasoning:
                parts.append(f"\n## Analysis\n{reasoning[:500]}")

        if not parts:
            return "No relevant results found."

        total = (len(results.memories or [])
                 + len(results.resources or [])
                 + len(results.skills or []))
        return f"Smart search: {total} results\n\n" + "\n".join(parts)

    @mcp.tool()
    async def add_resource(resource_path: str) -> str:
        """Add a file, directory, or URL to the knowledge base."""
        def _sync():
            client = _get_client()
            path = resource_path
            if not path.startswith("http"):
                resolved = Path(path).expanduser()
                if not resolved.exists():
                    return f"Error: File not found: {resolved}"
                path = str(resolved)
            result = client.add_resource(path=path)
            if result and "root_uri" in result:
                root_uri = result["root_uri"]
                try:
                    client.wait_processed(timeout=120)
                except Exception:
                    pass
                return f"Resource added and indexed: {root_uri}"
            elif result and result.get("status") == "error":
                errors = result.get("errors", [])[:3]
                return f"Error: {'; '.join(errors)}"
            return "Failed to add resource."

        return await asyncio.to_thread(_sync)

    @mcp.tool()
    async def session_commit(
        messages_json: str,
        session_id: str = "",
    ) -> str:
        """Extract structured memories from a conversation.
        Identifies: profile, preferences, entities, events, cases, patterns.
        Input: JSON array of {role, content} messages."""
        def _sync():
            client = _get_client()
            try:
                msgs = json.loads(messages_json)
            except json.JSONDecodeError as e:
                return f"Invalid JSON: {e}"

            session = client.session(session_id or None)
            for msg in msgs:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    session.add_message(role, content)

            result = session.commit()
            extracted = result.get("memories_extracted", 0)
            archived = result.get("archived", False)
            sid = result.get("session_id", "")
            return (
                f"Session committed: {sid}\n"
                f"  Memories extracted: {extracted}\n"
                f"  Archived: {archived}\n"
                f"  Stats: {json.dumps(result.get('stats', {}))}")

        return await asyncio.to_thread(_sync)

    @mcp.resource("openviking://status")
    def server_status() -> str:
        return json.dumps({
            "config_path": _config_path,
            "data_path": _data_path,
            "status": "running",
            "tools": ["query", "search", "smart_search",
                      "add_resource", "session_commit"],
        }, indent=2)

    return mcp


def main():
    global _config_path, _data_path

    parser = argparse.ArgumentParser(
        description="OpenViking MCP Server")
    parser.add_argument("--config", type=str, default=_config_path)
    parser.add_argument("--data", type=str, default=_data_path)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(
        os.getenv("OPENVIKING_PORT", "2033")))
    parser.add_argument("--transport", type=str,
                        choices=["streamable-http", "stdio"],
                        default="streamable-http")
    args = parser.parse_args()

    _config_path = args.config
    _data_path = args.data

    if os.getenv("OV_DEBUG") == "1":
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("OpenViking MCP Server starting")
    logger.info(f"  config: {_config_path}")
    logger.info(f"  data:   {_data_path}")

    mcp = create_server(host=args.host, port=args.port)

    if args.transport == "streamable-http":
        logger.info(f"  endpoint: http://{args.host}:{args.port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
