export default defineBackground(() => {
  browser.runtime.onInstalled.addListener(({ reason }) => {
    console.log("Yubal extension installed:", reason);
  });
});
