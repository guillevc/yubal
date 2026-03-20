export const basePath: string = new URL(document.baseURI).pathname.replace(
  /\/$/,
  "",
);
