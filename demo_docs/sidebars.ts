import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Pages from source',
      collapsed: false,
      items: [
      "document/nanotechnology-perceptions",
      "document/nanotechnology-perceptions-vol-20-no-s9-2024",
      "document/background",
      "document/figure-2-digital-signal-processing-system",
      "document/the-fast-fourier-transform",
      "document/methodology",
      "document/results-and-discussions",
      "document/figure-8-resultant-filter-coefficients",
      "document/figure-11-audio-signal-in-corporation-section",
      "document/figure-14-frequency-spectra-of-the-line-section",
      "document/figure-16-project-graphical-interface",
      "document/figure-17-signal-spectrum-plot-code",
      "document/nanotechnology-perceptions-vol-20-no-s9-2024-2"
      ],
    },
  ],
};

export default sidebars;
