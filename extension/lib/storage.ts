import { storage } from "wxt/utils/storage";

export const yubalUrl = storage.defineItem<string>("sync:yubalUrl");
export const yubalUrlDraft = storage.defineItem<string>(
  "session:yubalUrlDraft",
);
