"""
网页浏览器工具测试

测试 WebBrowserTool 的 URL 抓取、HTML 转文本、无效 URL 处理、超时处理等功能。
"""
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agent_forge.tools.web_browser import WebBrowserTool


class MockResponse:
    """模拟 httpx 响应"""

    def __init__(self, text: str, status_code: int = 200, content_type: str = "text/html"):
        self._text = text
        self.status_code = status_code
        self.content = text.encode("utf-8")
        self.headers = {"content-type": content_type}

    @property
    def text(self):
        return self._text


class TestWebBrowserTool:
    """测试网页浏览器工具"""

    @pytest.fixture
    def tool(self):
        return WebBrowserTool()

    @pytest.mark.asyncio
    async def test_fetch_url(self, tool):
        """测试正常 URL 抓取"""
        html_content = "<html><body><h1>Test Page</h1><p>Hello, AgentForge!</p></body></html>"

        async def mock_get(url, **kwargs):
            return MockResponse(text=html_content, status_code=200)

        with patch.object(tool, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_factory.return_value = mock_client

            result = await tool.execute(url="https://example.com")

        assert "Test Page" in result
        assert "Hello, AgentForge!" in result

    @pytest.mark.asyncio
    async def test_html_to_text_conversion(self, tool):
        """测试 HTML 转文本效果"""
        html_content = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Title</h1>
            <p>Paragraph one.</p>
            <p>Paragraph two.</p>
            <script>alert('xss')</script>
            <style>.cls{color:red}</style>
        </body>
        </html>
        """

        async def mock_get(url, **kwargs):
            return MockResponse(text=html_content, status_code=200)

        with patch.object(tool, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_factory.return_value = mock_client

            result = await tool.execute(url="https://example.com")

        # 应保留标题和段落文本
        assert "Title" in result
        assert "Paragraph one" in result
        assert "Paragraph two" in result
        # 应去除脚本和样式内容
        assert "alert" not in result
        assert "xss" not in result
        assert "color:red" not in result

    @pytest.mark.asyncio
    async def test_invalid_url(self, tool):
        """测试无效 URL 处理"""
        result = await tool.execute(url="not-a-valid-url")
        assert "格式无效" in result

        result = await tool.execute(url="")
        assert "不能为空" in result

    @pytest.mark.asyncio
    async def test_timeout(self, tool):
        """测试 HTTP 超时处理"""
        async def mock_get(url, **kwargs):
            raise httpx.TimeoutException("请求超时", request=None)

        with patch.object(tool, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_factory.return_value = mock_client

            result = await tool.execute(url="https://example.com")

        assert "超时" in result

    @pytest.mark.asyncio
    async def test_http_404(self, tool):
        """测试 404 页面处理"""
        async def mock_get(url, **kwargs):
            return MockResponse(text="Not Found", status_code=404)

        with patch.object(tool, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_factory.return_value = mock_client

            result = await tool.execute(url="https://example.com/notfound")

        assert "404" in result or "不存在" in result

    @pytest.mark.asyncio
    async def test_http_403(self, tool):
        """测试 403 禁止访问处理"""
        async def mock_get(url, **kwargs):
            return MockResponse(text="Forbidden", status_code=403)

        with patch.object(tool, "_get_client") as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.get = mock_get
            mock_client_factory.return_value = mock_client

            result = await tool.execute(url="https://example.com/forbidden")

        assert "403" in result or "拒绝" in result

    @pytest.mark.asyncio
    async def test_private_url_blocked(self, tool):
        """测试内网地址被阻止"""
        result = await tool.execute(url="http://localhost:8000/secret")
        assert "内网" in result or "拒绝" in result

        result = await tool.execute(url="http://127.0.0.1/secret")
        assert "内网" in result or "拒绝" in result

        result = await tool.execute(url="http://10.0.0.1/admin")
        assert "内网" in result or "拒绝" in result
