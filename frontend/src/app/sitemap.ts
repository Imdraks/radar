import { MetadataRoute } from "next";
import { documentation, documentationUpdated } from '@/content/documentation';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://radarapp.fr";

  return [
    { url: `${baseUrl}/mcp`, lastModified: documentationUpdated, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${baseUrl}/doc`, lastModified: documentationUpdated, changeFrequency: 'monthly', priority: 0.8 },
    ...documentation.map(article => ({ url: `${baseUrl}/doc/${article.slug}`, lastModified: documentationUpdated, changeFrequency: 'monthly' as const, priority: 0.6 })),
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/contact`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/legal`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];
}
