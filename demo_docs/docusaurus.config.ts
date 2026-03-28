import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const siteTitle = process.env.DOCUSAURUS_SITE_TITLE || 'AccessDocs';

const config: Config = {
  title: siteTitle,
  tagline: '',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://example.com',
  baseUrl: process.env.DOCUSAURUS_BASE_URL || '/',

  onBrokenLinks: 'warn',

  // PDF-extracted docs often contain "<3s", "{ ... }" snippets, etc. MDX would treat those as JSX.
  markdown: {
    format: 'md',
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        language: ['en'],
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: siteTitle,
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docSidebar',
          position: 'left',
          label: 'Contents',
        },
      ],
    },
    footer: {
      copyright: `© ${new Date().getFullYear()}`,
    },
    colorMode: {
      respectPrefersColorScheme: true,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
