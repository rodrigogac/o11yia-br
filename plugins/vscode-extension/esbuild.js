// Bundle da extensão com esbuild.
// Uso: node esbuild.js [--production] [--watch]
const esbuild = require("esbuild");

const production = process.argv.includes("--production");
const watch = process.argv.includes("--watch");

/** @type {import('esbuild').BuildOptions} */
const options = {
  entryPoints: ["src/extension.ts"],
  bundle: true,
  format: "cjs",
  platform: "node",
  target: "node18",
  outfile: "out/extension.js",
  // 'vscode' é fornecido pelo runtime do VSCode — nunca deve ser bundleado.
  external: ["vscode"],
  sourcemap: !production,
  minify: production,
  logLevel: "info",
};

async function main() {
  if (watch) {
    const ctx = await esbuild.context(options);
    await ctx.watch();
    console.log("[esbuild] watching...");
  } else {
    await esbuild.build(options);
    console.log("[esbuild] build done");
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
