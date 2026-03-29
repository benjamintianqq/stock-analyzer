/**
 * Cloudflare Worker - CORS 代理
 * 部署到子域名: stock-proxy.benjamin-stock-analyzer.org
 *
 * 用法: https://stock-proxy.benjamin-stock-analyzer.org/?url=<目标URL>
 * 返回: { contents: "<原始响应内容>" }
 */

export default {
  async fetch(request) {
    const corsHeaders = {
      'Access-Control-Allow-Origin': 'https://benjamin-stock-analyzer.org',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    const { searchParams } = new URL(request.url);
    const target = searchParams.get('url');

    if (!target) {
      return new Response(JSON.stringify({ error: 'missing ?url=' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 只允许请求金融数据源，防止滥用
    const allowed = [
      'qq.com', 'gtimg.cn',
      'eastmoney.com',
      '10jqka.com.cn', 'thsi.cn',
      'finance.yahoo.com',
    ];
    const targetHost = new URL(target).hostname;
    if (!allowed.some(d => targetHost.endsWith(d))) {
      return new Response(JSON.stringify({ error: 'domain not allowed' }), {
        status: 403,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    try {
      const res = await fetch(target, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          'Referer': new URL(target).origin,
          'Accept': '*/*',
        },
        cf: { cacheTtl: 30, cacheEverything: false },
      });

      const contentType = res.headers.get('content-type') || '';
      // Cloudflare Worker 运行环境自动处理编码，直接读 text
      const body = await res.text();

      return new Response(JSON.stringify({ contents: body }), {
        status: 200,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json; charset=utf-8',
          'Cache-Control': 'no-cache',
        },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 502,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
  },
};
