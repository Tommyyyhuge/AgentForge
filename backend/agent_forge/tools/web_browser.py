"""
AgentForge 网页浏览器工具模块

使用 httpx 获取网页内容并进行 HTML 到文本的转换。
支持基本的网页抓取和内容提取。
"""
import logging
import re
from typing import Any, Dict, Optional

import httpx

from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 默认请求超时（秒）
_DEFAULT_TIMEOUT: float = 15.0

# 最大响应体大小（5MB）
_MAX_RESPONSE_SIZE: int = 5 * 1024 * 1024

# 最大返回文本长度
_MAX_OUTPUT_LENGTH: int = 50000

# 常见 User-Agent
_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def _html_to_text(html: str) -> str:
    """将 HTML 转换为纯文本

    去除所有 HTML 标签、脚本和样式内容，
    保留基本的文本结构和换行。

    Args:
        html: 原始 HTML 字符串

    Returns:
        提取的纯文本内容
    """
    # 移除 <script> 及其内容
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # 移除 <style> 及其内容
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # 移除 <noscript> 及其内容
    text = re.sub(r"<noscript[^>]*>.*?</noscript>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # 将块级标签替换为换行符
    for tag in ["p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6",
                 "li", "tr", "blockquote", "section", "header", "footer"]:
        text = re.sub(
            rf"<{tag}[^>]*>", "\n", text, flags=re.IGNORECASE
        )
        text = re.sub(
            rf"</{tag}>", "\n", text, flags=re.IGNORECASE
        )

    # 移除所有剩余 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)

    # 解码 HTML 实体
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    # 合并多余空行（保留最多连续 2 个换行）
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 移除每行首尾空白
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)

    return text.strip()


class WebBrowserTool(BaseTool):
    """网页浏览器工具

    使用 httpx 获取网页内容并将 HTML 转换为可读的纯文本。
    适用于快速获取网页信息、文档和文章内容。

    注意：复杂网页（JavaScript 渲染、动态内容等）可能无法完整获取。
    """

    name: str = "web_browser"
    description: str = "获取网页内容并转换为可读文本，支持标准 HTML 页面"
    version: str = "1.0"

    def __init__(self):
        """初始化浏览器工具"""
        self._http_client: Optional[httpx.AsyncClient] = None
        super().__init__()

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端

        Returns:
            httpx.AsyncClient 实例
        """
        if self._http_client is None or self._http_client.is_closed:
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=20,
            )
            self._http_client = httpx.AsyncClient(
                follow_redirects=True,
                timeout=_DEFAULT_TIMEOUT,
                limits=limits,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,*/*;q=0.8"
                    ),
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )
        return self._http_client

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义网页浏览工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "url": {
                    "type": "string",
                    "description": "要获取的网页 URL（完整 URL，含 http:// 或 https://）",
                },
            },
            required=["url"],
            examples=[
                {"url": "https://docs.python.org/3/library/asyncio.html"},
                {"url": "https://example.com"},
            ],
        )

    async def execute(self, **kwargs) -> str:
        """获取网页内容

        Args:
            **kwargs: 工具参数，包含:
                - url: 目标网页的完整 URL

        Returns:
            网页的纯文本内容
        """
        url: str = kwargs.get("url", "")

        logger.info("web_browser 开始获取: %s", url)

        if not url or not url.strip():
            return "[网页浏览错误] URL 不能为空"

        url = url.strip()

        # URL 格式校验
        if not url.startswith(("http://", "https://")):
            logger.warning("web_browser URL 格式无效: %s", url)
            return (
                "[网页浏览错误] URL 格式无效，必须以 http:// 或 https:// 开头"
            )

        # 基础安全校验：拒绝内网地址
        if self._is_private_url(url):
            logger.warning("web_browser 拒绝内网地址: %s", url)
            return f"[网页浏览安全错误] 拒绝访问内网地址: {url}"

        client = await self._get_client()

        try:
            response = await client.get(url)

            # 检查状态码
            if response.status_code == 404:
                return f"[网页浏览错误] 页面不存在 (404): {url}"
            if response.status_code == 403:
                return f"[网页浏览错误] 访问被拒绝 (403): {url}"
            if response.status_code >= 400:
                return (
                    f"[网页浏览错误] HTTP {response.status_code}: {url}"
                )

            # 检查响应大小
            content = response.content
            if len(content) > _MAX_RESPONSE_SIZE:
                logger.warning(
                    "web_browser 响应过大: %d bytes", len(content)
                )
                return (
                    f"[网页浏览错误] 页面过大 ({len(content) / 1024 / 1024:.1f}MB)，"
                    f"超过限制 ({_MAX_RESPONSE_SIZE / 1024 / 1024:.0f}MB)"
                )

            # 检查内容类型，确保是 HTML
            content_type: str = response.headers.get("content-type", "")
            if "text" not in content_type and "html" not in content_type:
                logger.warning(
                    "web_browser 非 HTML 内容: %s", content_type
                )
                return (
                    f"[网页浏览提示] 返回内容类型为 {content_type}，"
                    "非 HTML 页面，可能无法正常显示。\n\n"
                    f"{_html_to_text(response.text)[:_MAX_OUTPUT_LENGTH]}"
                )

            # HTML 转文本
            text: str = _html_to_text(response.text)

            # 输出截断
            if len(text) > _MAX_OUTPUT_LENGTH:
                text = text[:_MAX_OUTPUT_LENGTH]
                text += (
                    f"\n\n... (内容已截断，共 {len(response.text)} 字符)"
                )

            logger.info(
                "web_browser 获取完成: %s (%d 字符)", url, len(text)
            )
            return text

        except httpx.TimeoutException:
            logger.warning("web_browser 请求超时: %s", url)
            return f"[网页浏览错误] 请求超时 ({_DEFAULT_TIMEOUT}s): {url}"
        except httpx.ConnectError as e:
            logger.warning("web_browser 连接失败: %s - %s", url, e)
            return f"[网页浏览错误] 连接失败: {e}"
        except httpx.InvalidURL:
            return f"[网页浏览错误] URL 格式无效: {url}"
        except httpx.HTTPError as e:
            logger.warning("web_browser HTTP 错误: %s - %s", url, e)
            return f"[网页浏览错误] HTTP 请求失败: {e}"
        except Exception as e:
            logger.error("web_browser 未知错误: %s - %s", url, e)
            return f"[网页浏览错误] 未知错误: {e}"

    def _is_private_url(self, url: str) -> bool:
        """检查 URL 是否为内网地址

        安全措施：阻止对私有 IP 和内网地址的请求。

        Args:
            url: 完整的 URL 字符串

        Returns:
            是否为内网地址
        """
        import urllib.parse

        try:
            parsed = urllib.parse.urlparse(url)
            hostname: str = parsed.hostname or ""

            # 检测内网主机名
            private_hosts: tuple = (
                "localhost",
                "127.0.0.1",
                "::1",
                "0.0.0.0",
            )
            if hostname in private_hosts:
                return True

            # 检测内网 IP 段
            private_prefixes: tuple = (
                "10.",
                "172.16.",
                "172.17.",
                "172.18.",
                "172.19.",
                "172.20.",
                "172.21.",
                "172.22.",
                "172.23.",
                "172.24.",
                "172.25.",
                "172.26.",
                "172.27.",
                "172.28.",
                "172.29.",
                "172.30.",
                "172.31.",
                "192.168.",
            )
            if hostname.startswith(private_prefixes):
                return True

            return False

        except Exception:
            return False

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            logger.debug("web_browser HTTP 客户端已关闭")


__all__ = ["WebBrowserTool"]
