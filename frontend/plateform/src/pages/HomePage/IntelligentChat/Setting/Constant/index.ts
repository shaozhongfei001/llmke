export const ASSISTANT_MIN_MAX = {
  top_k: {
    default: 10,
    min: 1,
    max: 15
  },
  max_tokens: {
    default: 4096,
    min: 0,
    max: 10000
  },
  max_round: {
    default: 5,
    min: 0,
    max: 32
  },
  database_name: {
    default: []
  }
};
