import { createModel } from "@rematch/core";

export const global = createModel()({
  state: {
    siderBarWidth: 80,
    theme: "default",
    collapsed: true,
    globalMenu: null,
    prevRoute: ""
  },
  reducers: {
    SET_PREV_ROUTE: (state, payload: any) => {
      return { ...state, prevRoute: payload };
    },
    SET_GLOBAL_STATE: (state, payload: any) => {
      // Ensure that the payload is an object and not null
      if (typeof payload !== "object" || payload === null) {
        // If the payload is invalid, return the current state without changes
        return state;
      }

      // Create a new state object by merging the current state with the payload
      // This will overwrite any existing properties in state with those in payload
      // and add any new properties from payload to the state
      return { ...state, ...payload };
    },
    TOGGLE_COLLAPSED: (state) => {
      console.log(state);
      return { ...state, collapsed: !state.collapsed };
    },
    SET_GLOBAL_MENU: (state, payload: any) => {
      return { ...state, globalMenu: payload };
    }
  }
});
