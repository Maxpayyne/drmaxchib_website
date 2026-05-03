<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="/rss/channel/title"/> — RSS Feed</title>
        <style>
          :root {
            --bg: #fdfcf7;
            --surface: #faf7ef;
            --border: #e8dfca;
            --text: #1a1a18;
            --text-muted: #6b6b66;
            --accent: #2f5734;
          }
          @media (prefers-color-scheme: dark) {
            :root {
              --bg: #0e1410;
              --surface: #1a221c;
              --border: #2c352e;
              --text: #faf7ef;
              --text-muted: #9ba39c;
              --accent: #8eb190;
            }
          }
          html { background: var(--bg); }
          body {
            font-family: 'Inter Tight', system-ui, sans-serif;
            color: var(--text);
            max-width: 56rem;
            margin: 0 auto;
            padding: 3rem 1.5rem 5rem;
            line-height: 1.6;
          }
          .banner {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 2.5rem;
            font-size: 0.9375rem;
            color: var(--text-muted);
          }
          .banner strong { color: var(--accent); }
          h1 {
            font-family: 'Fraunces', Georgia, serif;
            font-size: clamp(2rem, 5vw, 3rem);
            letter-spacing: -0.025em;
            font-weight: 500;
            margin: 0 0 0.5rem;
          }
          .desc { color: var(--text-muted); margin: 0 0 3rem; max-width: 60ch; }
          .item {
            border-top: 1px solid var(--border);
            padding: 1.5rem 0;
          }
          .item:last-child { border-bottom: 1px solid var(--border); }
          .item h2 {
            font-family: 'Fraunces', Georgia, serif;
            font-size: 1.375rem;
            margin: 0 0 0.5rem;
            font-weight: 500;
          }
          .item h2 a {
            color: var(--text);
            text-decoration: none;
          }
          .item h2 a:hover { color: var(--accent); }
          .date {
            font-family: ui-monospace, 'SF Mono', monospace;
            font-size: 0.8125rem;
            color: var(--text-muted);
            margin: 0 0 0.75rem;
          }
          .item p { color: var(--text-muted); margin: 0; }
          a { color: var(--accent); }
        </style>
      </head>
      <body>
        <div class="banner">
          <strong>This is an RSS feed.</strong> Subscribe by copying this page's
          URL into a feed reader (Feedly, NetNewsWire, Reeder, etc.) for new posts
          delivered automatically.
        </div>
        <h1><xsl:value-of select="/rss/channel/title"/></h1>
        <p class="desc"><xsl:value-of select="/rss/channel/description"/></p>
        <xsl:for-each select="/rss/channel/item">
          <article class="item">
            <h2>
              <a href="{link}"><xsl:value-of select="title"/></a>
            </h2>
            <p class="date"><xsl:value-of select="pubDate"/></p>
            <p><xsl:value-of select="description"/></p>
          </article>
        </xsl:for-each>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
