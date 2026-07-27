import { defineConfig, loadEnv } from 'vite';
import { writeFileSync } from 'node:fs';
import path from 'node:path';

const RESERVED_INVALID_RE = /\.invalid(\/|$)/i;
const PLACEHOLDER_RE = /example\.(com|org|net)|your-domain|changeme|localhost/i;

const TEST_PROFILE_DEFAULTS = {
  EIF_SITE_URL: 'https://eif-site.invalid/',
  EIF_REPOSITORY_URL: 'https://github.invalid/eif-website-test-profile',
};

// The repository URL is a public, permanent fact about this project, not a
// per-deployment input, so it has a committed default and resolves in every
// mode. It used to be production-only, which was right while publication was
// an undecided owner call: dev and preview pointed the closing screen's
// Source row at an on-page anchor and printed "the repository link is added
// at publication". Once the repository is public that link is simply broken
// in every mode but one, and that line is false. EIF_SITE_URL keeps its
// production gate, because canonical, sitemap and robots output must not
// leak out of a production build.
const DEFAULT_REPOSITORY_URL =
  'https://github.com/mike-arbuzov365/engineering-intelligence-framework';

export function normalizePublicUrl(name, value, mode, { directory = false } = {}) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`[eif-site] ${name}="${value}" must be a valid https:// URL for a ${mode} build.`);
  }

  if (parsed.protocol !== 'https:' || parsed.username || parsed.password) {
    throw new Error(
      `[eif-site] ${name}="${value}" must be a credential-free https:// URL for a ${mode} build.`,
    );
  }
  if (parsed.search || parsed.hash) {
    throw new Error(`[eif-site] ${name}="${value}" must not contain a query or fragment.`);
  }

  if (directory && !parsed.pathname.endsWith('/')) {
    parsed.pathname += '/';
  }
  return parsed.toString();
}

function checkPublicUrl(name, value, mode, { directory = false, isTestProduction = false } = {}) {
  if (!value) {
    throw new Error(`[eif-site] ${name} is required for a ${mode} build and was not set.`);
  }
  const isReservedInvalid = RESERVED_INVALID_RE.test(value);
  if (isReservedInvalid && !isTestProduction) {
    throw new Error(`[eif-site] ${name}="${value}" uses the reserved .invalid test domain outside build:test-production.`);
  }
  if (!isReservedInvalid && PLACEHOLDER_RE.test(value)) {
    throw new Error(`[eif-site] ${name}="${value}" looks like a placeholder value; refusing a ${mode} build.`);
  }
  return normalizePublicUrl(name, value, mode, { directory });
}

// Resolved in every mode, including dev. An override still has to be a
// credential-free https URL, so a mistyped one fails the build rather than
// shipping as the reader's first command.
export function resolveRepositoryUrl(mode, env) {
  const isTestProduction = mode === 'test-production';
  const value =
    env.EIF_REPOSITORY_URL ||
    (isTestProduction ? TEST_PROFILE_DEFAULTS.EIF_REPOSITORY_URL : DEFAULT_REPOSITORY_URL);
  return checkPublicUrl('EIF_REPOSITORY_URL', value, mode, { isTestProduction });
}

export function resolveProductionUrls(mode, env) {
  const isTestProduction = mode === 'test-production';
  const siteUrl = checkPublicUrl(
    'EIF_SITE_URL',
    env.EIF_SITE_URL || (isTestProduction ? TEST_PROFILE_DEFAULTS.EIF_SITE_URL : ''),
    mode,
    { directory: true, isTestProduction },
  );

  return { siteUrl, repositoryUrl: resolveRepositoryUrl(mode, env) };
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

      // The label is the same promise in both languages, and there is no
      // second state to caption any more: the repository URL resolves in
      // every mode, so the closing screen's Source row and the quickstart's
      // `git clone` line are the real ones whether this is dev, preview or
      // production. The "link added at publication" line that used to sit
      // under the CTA described a decision that has since been made.
      let out = html
        .replaceAll('__EIF_REPO_CTA_HREF__', repositoryUrl)
        .replaceAll('__EIF_REPO_CLONE_URL__', repositoryUrl)
        .replaceAll('__EIF_REPO_CTA_LABEL_EN__', 'Public repository')
        .replaceAll('__EIF_REPO_CTA_LABEL_UK__', 'Публічний репозиторій');

      const tags = [];
      if (siteUrl) {
        const canonical = siteUrl;
        const socialImage = new URL('social-card.png', siteUrl).toString();
        // Matched by filename rather than by the exact source string. Vite
        // rebases root-relative asset paths against `base` before this hook
        // runs, so on a deployment sub-path the meta content is already
        // "/<base>/social-card.png" and a literal "/social-card.png" replace
        // silently matches nothing - shipping a relative social image that
        // no crawler can resolve. Only a root-domain site URL ever hid that.
        out = out.replace(/content="[^"]*\/social-card\.png"/g, `content="${socialImage}"`);
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
        ? `User-agent: *\nAllow: /\nSitemap: ${new URL('sitemap.xml', siteUrl).toString()}\n`
        : `User-agent: *\nDisallow: /\n`;
      writeFileSync(path.join(outDir, 'robots.txt'), robots);

      if (siteUrl) {
        const loc = siteUrl;
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
  // Resolved for every mode, dev included, so the closing screen's Source row
  // and the quickstart's clone line point at the real repository whatever
  // this build is for.
  let repositoryUrl = resolveRepositoryUrl(mode, env);
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
    // Production can be hosted at a sub-path (for example /eif/) without
    // breaking Vite-emitted assets or public/ URLs. Preview keeps the normal
    // root base because it has no owner-supplied public URL.
    base: siteUrl ? new URL(siteUrl).pathname : '/',
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
