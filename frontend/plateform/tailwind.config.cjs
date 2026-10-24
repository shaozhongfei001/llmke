/* eslint-disable no-undef */
// eslint-disable-next-line @typescript-eslint/no-var-requires
const colors = require("tailwindcss/colors");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{mdx,html,ts,tsx}"],
  mode: "jit",
  prefix: "",
  important: false,
  theme: {
    fontFamily: {
      SC: ["PingFang SC"]
    },
    extend: {
      colors: {
        "gray-2a": "#2a2a2a",
        "text-color1": "#222222",
        "text-color2": "#555555",
        "text-color3": "#999999",
        "primary-color": "#055AFF"
      }
    }
  },
  // plugins: [require('tailwind-scrollbar-hide'), require('@tailwindcss/line-clamp')],
  plugins: [
    require("@tailwindcss/container-queries"),
    require("@tailwindcss/typography")
  ],
  corePlugins: {
    preflight: false
  }
};
