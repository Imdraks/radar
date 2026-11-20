"use client";
import { useEffect, useState } from "react";
import DOMPurify from "dompurify";
/** Imported/provider HTML is data, never executable markup or a remote image beacon. */
export function SafeHtml({
  html,
  className,
}: {
  html: string;
  className?: string;
}) {
  const [safe, setSafe] = useState("");
  useEffect(
    () =>
      setSafe(
        DOMPurify.sanitize(html, {
          ALLOWED_TAGS: [
            "p",
            "br",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "s",
            "ul",
            "ol",
            "li",
            "blockquote",
            "pre",
            "code",
            "h1",
            "h2",
            "h3",
            "h4",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "a",
            "hr",
            "span",
            "div",
          ],
          ALLOWED_ATTR: ["href", "title", "colspan", "rowspan"],
          ALLOW_DATA_ATTR: false,
          ALLOW_ARIA_ATTR: false,
        }),
      ),
    [html],
  );
  return (
    <div className={className} dangerouslySetInnerHTML={{ __html: safe }} />
  );
}
