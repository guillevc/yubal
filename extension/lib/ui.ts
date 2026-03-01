export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs?: Record<string, string> | null,
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  if (attrs) {
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "class") {
        element.className = value;
      } else {
        element.setAttribute(key, value);
      }
    }
  }
  for (const child of children) {
    element.append(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return element;
}

type ButtonState = "idle" | "loading" | "success" | "error";

interface ButtonStateOpts {
  idleText: string;
  successText: string;
  errorText: string;
  onClick: () => Promise<void>;
}

export function setButtonState(
  btn: HTMLButtonElement,
  state: ButtonState,
  opts: ButtonStateOpts,
) {
  // Clear any existing auto-reset timer
  const timerId = (btn as any).__resetTimer;
  if (timerId) clearTimeout(timerId);

  btn.disabled = state === "loading";

  switch (state) {
    case "idle":
      btn.innerHTML = opts.idleText;
      btn.onclick = async () => {
        setButtonState(btn, "loading", opts);
        await opts.onClick();
      };
      break;
    case "loading":
      btn.innerHTML = `<span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent align-middle"></span>`;
      btn.onclick = null;
      break;
    case "success":
      btn.innerHTML = opts.successText;
      btn.onclick = null;
      (btn as any).__resetTimer = setTimeout(
        () => setButtonState(btn, "idle", opts),
        2500,
      );
      break;
    case "error":
      btn.innerHTML = opts.errorText;
      // Clicking in error state immediately retries
      btn.onclick = async () => {
        setButtonState(btn, "loading", opts);
        await opts.onClick();
      };
      (btn as any).__resetTimer = setTimeout(
        () => setButtonState(btn, "idle", opts),
        3000,
      );
      break;
  }
}
