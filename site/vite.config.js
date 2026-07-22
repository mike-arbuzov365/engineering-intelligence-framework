import { defineConfig, loadEnv } from 'vite';
import { writeFileSync } from 'node:fs';
import path from 'node:path';

const HTTPS_URL_RE = /^https:\/\/\S+$/;
const RESERVED_INVALID_RE = /\.invalid(\/|$)/i;
const PLACEHOLDER_RE = /example\.(com|org|net)|your-domain|changeme|localhost/i;

const TEST_PROFILE_DEFAULTS = {
  EIF_SITE_URL: 'https://eif-site.invalid/',
  EIF_REPOSITORY_URL: 'https://github.invalid/eif-website-test-profile',
};

function resolveProductionUrls(mode, env) {
  const isTestProduction = mode === 'test-production';
  const defaults = isTestProduction ? TEST_PROFILE_DEFAULTS : {};

  const siteUrl = env.EIF_SITE_URL || defaults.EIF_SITE_URL || '';
  const repositoryUrl = env.EIF_REPOSITORY_URL || defaults.EIF_REPOSITORY_URL || '';

  for (const [name, value] of [
    ['EIF_SITE_URL', siteUrl],
    ['EIF_REPOSITORY_URL', repositoryUrl],
  ]) {
    if (!value) {
      throw new Error(`[eif-site] ${name} is required for a ${mode} build and was not set.`);
    }
    if (!HTTPS_URL_RE.test(value)) {
      throw new Error(`[eif-site] ${name}="${value}" must be a non-placeholder https:// URL for a ${mode} build.`);
    }
    const isReservedInvalid = RESERVED_INVALID_RE.test(value);
    if (isReservedInvalid && !isTestProduction) {
      throw new Error(`[eif-site] ${name}="${value}" uses the reserved .invalid test domain outside build:test-production.`);
    }
    if (!isReservedInvalid && PLACEHOLDER_RE.test(value)) {
      throw new Error(`[eif-site] ${name}="${value}" looks like a placeholder value; refusing a ${mode} build.`);
    }
  }

  return { siteUrl, repositoryUrl };
}

function eifDeployStatusPlugin(getDeployStatus) {
  return {
    name: 'eif-deploy-status',
    transformIndexHtml() {
      return [
        {
          tag: 'meta',
          injectTo: 'head',
          attrs: { name: 'eif:deploy-status', content: getDeployStatus() },
        },
      ];
    },
  };
}

// Static-HTML metadata substitution and dist/robots.txt + dist/sitemap.xml
// generation, all resolved at build time so no-JS visitors get the correct
// per-mode result with zero runtime branching (D-09).
function eifMetadataPlugin(getUrls) {
  return {
    name: 'eif-metadata',
    transformIndexHtml(html) {
      const { siteUrl, repositoryUrl } = getUrls();
      const repoHref = repositoryUrl || '#evidence';
      const repoLabel = repositoryUrl
        ? 'Public repository'
        : 'Public repository (link added at publication)';

      let out = html
        .replaceAll('__EIF_REPO_CTA_HREF__', repoHref)
        .replaceAll('__EIF_REPO_CTA_LABEL__', repoLabel);

      const tags = [];
      if (siteUrl) {
        const canonical = new URL('/', siteUrl).toString();
        tags.push({ tag: 'link', injectTo: 'head', attrs: { rel: 'canonical', href: canonical } });
        tags.push({
          tag: 'meta',
          injectTo: 'head',
          attrs: { property: 'og:url', content: canonical },
        });
      }
      return { html: out, tags };
    },
    writeBundle(options) {
      const outDir = options.dir ?? 'dist';
      const { siteUrl } = getUrls();

      const robots = siteUrl
        ? `User-agent: *\nAllow: /\nSitemap: ${new URL('/sitemap.xml', siteUrl).toString()}\n`
        : `User-agent: *\nDisallow: /\n`;
      writeFileSync(path.join(outDir, 'robots.txt'), robots);

      if (siteUrl) {
        const loc = new URL('/', siteUrl).toString();
        const sitemap =
          `<?xml version="1.0" encoding="UTF-8"?>\n` +
          `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
          `  <url><loc>${loc}</loc></url>\n` +
          `</urlset>\n`;
        writeFileSync(path.join(outDir, 'sitemap.xml'), sitemap);
      }
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'EIF_');
  const isProduction = mode === 'production';
  const isTestProduction = mode === 'test-production';

  let siteUrl = '';
  let repositoryUrl = '';
  // 'no-deploy' is the fail-safe default: only a real `production` build with
  // validated URLs flips this to 'deployable'. See D-09 in
  // 03-DECISIONS-001-ratified-implementation-defaults.md (private planning repo).
  let deployStatus = 'no-deploy';

  if (isProduction || isTestProduction) {
    ({ siteUrl, repositoryUrl } = resolveProductionUrls(mode, env));
    deployStatus = isTestProduction ? 'no-deploy-test-profile' : 'deployable';
  }

  return {
    root: '.',
    plugins: [
      eifDeployStatusPlugin(() => deployStatus),
      eifMetadataPlugin(() => ({ siteUrl, repositoryUrl })),
    ],
    define: {
      __EIF_SITE_URL__: JSON.stringify(siteUrl),
      __EIF_REPOSITORY_URL__: JSON.stringify(repositoryUrl),
      __EIF_BUILD_MODE__: JSON.stringify(mode),
      __EIF_DEPLOY_STATUS__: JSON.stringify(deployStatus),
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
    },
  };
});
