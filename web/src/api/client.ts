import createClient from "openapi-fetch";
import { basePath } from "@/lib/base-path";
import type { paths } from "./schema";

export const api = createClient<paths>({
  baseUrl: `${basePath}/api`,
});
