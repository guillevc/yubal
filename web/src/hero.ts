import { heroui } from "@heroui/react";

export default heroui({
  themes: {
    flexoki: {
      extend: "dark",
      colors: {
        // Backgrounds
        background: "#100F0F", // black

        // Content layers (surfaces)
        content1: "#1C1B1A", // base-950
        content2: "#282726", // base-900
        content3: "#343331", // base-850
        content4: "#403E3C", // base-800

        // Foreground (text)
        foreground: {
          DEFAULT: "#CECDC3", // base-200 (tx)
          50: "#100F0F",
          100: "#1C1B1A",
          200: "#282726",
          300: "#343331",
          400: "#575653", // base-700 (tx-3, faint)
          500: "#878580", // base-500 (tx-2, muted)
          600: "#B7B5AC", // base-300
          700: "#CECDC3", // base-200
          800: "#DAD8CE", // base-150
          900: "#FFFCF0", // paper (brightest)
        },

        // Default (neutral/gray scale)
        default: {
          50: "#1C1B1A", // base-950
          100: "#282726", // base-900
          200: "#343331", // base-850
          300: "#403E3C", // base-800
          400: "#575653", // base-700
          500: "#6F6E69", // base-600
          600: "#878580", // base-500
          700: "#B7B5AC", // base-300
          800: "#CECDC3", // base-200
          900: "#E6E4D9", // base-100
          DEFAULT: "#343331",
          foreground: "#CECDC3",
        },

        // Primary (cyan - links, active states)
        primary: {
          50: "#122F2C",
          100: "#143F3C",
          200: "#164F4A",
          300: "#1C6C66",
          400: "#24837B",
          500: "#2F968D",
          600: "#3AA99F", // cyan-400 (main)
          700: "#5ABDAC",
          800: "#87D3C3",
          900: "#DDF1E4",
          DEFAULT: "#3AA99F",
          foreground: "#100F0F",
        },

        // Secondary (purple)
        secondary: {
          50: "#1A1623",
          100: "#261C39",
          200: "#31234E",
          300: "#3C2A62",
          400: "#4F3685",
          500: "#5E409D",
          600: "#735EB5",
          700: "#8B7EC8", // purple-400 (main)
          800: "#A699D0",
          900: "#F0EAEC",
          DEFAULT: "#8B7EC8",
          foreground: "#100F0F",
        },

        // Success (green)
        success: {
          50: "#1A1E0C",
          100: "#252D09",
          200: "#313D07",
          300: "#3D4C07",
          400: "#536907",
          500: "#66800B",
          600: "#768D21",
          700: "#879A39", // green-400 (main)
          800: "#A0AF54",
          900: "#EDEECF",
          DEFAULT: "#879A39",
          foreground: "#100F0F",
        },

        // Warning (yellow/orange)
        warning: {
          50: "#27180E",
          100: "#40200D",
          200: "#59290D",
          300: "#71320D",
          400: "#9D4310",
          500: "#BC5215",
          600: "#CB6120",
          700: "#DA702C", // orange-400 (main)
          800: "#EC8B49",
          900: "#FFE7CE",
          DEFAULT: "#DA702C",
          foreground: "#100F0F",
        },

        // Danger (red)
        danger: {
          50: "#261312",
          100: "#3E1715",
          200: "#551B18",
          300: "#6C201C",
          400: "#942822",
          500: "#AF3029",
          600: "#C03E35",
          700: "#D14D41", // red-400 (main)
          800: "#E8705F",
          900: "#FFE1D5",
          DEFAULT: "#D14D41",
          foreground: "#FFFCF0",
        },

        // Divider
        divider: "#343331", // base-850

        // Focus ring
        focus: "#3AA99F", // cyan-400
      },
    },
  },
});
