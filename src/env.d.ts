/// <reference path="../.astro/types.d.ts" />
/// <reference types="@cloudflare/workers-types" />

type Runtime = import('@astrojs/cloudflare').Runtime<{ DB?: D1Database }>;

declare namespace App {
  interface Locals extends Runtime {}
}
