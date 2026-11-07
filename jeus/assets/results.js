window.JEUS_RESULTS = {
 "source": "Supplementary Data 1 of the manuscript",
 "open_models": [
  "GLM-5.3",
  "Qwen3.8-Flash-Next",
  "DeepSeek-V4.1-Flash",
  "MiMo-V2.6-Pro",
  "Kimi-K2.6"
 ],
 "benchmarks": [
  {
   "name": "BixBench",
   "metric": "accuracy (%)",
   "questions": 205,
   "scores": {
    "Jeus": 51.31707317073171,
    "Codex CLI": 49.46341463414634,
    "Claude Code": 47.90243902439025,
    "Biomni A1": 46.34146341463415
   }
  },
  {
   "name": "Verified-50",
   "metric": "accuracy (%)",
   "questions": 50,
   "scores": {
    "Jeus": 84.4,
    "Codex CLI": 82.4,
    "Claude Code": 82.8,
    "Biomni A1": 79.2
   }
  },
  {
   "name": "BAISBench",
   "metric": "official score (%)",
   "questions": 193,
   "scores": {
    "Jeus": 68.03108808290155,
    "Codex CLI": 61.398963730569946,
    "Claude Code": 65.07772020725389
   }
  }
 ],
 "memory": {
  "low": 4.0570012391573735,
  "high": 24.37142857142857,
  "comparisons": 28
 },
 "cost": {
  "low": 24.260186558567344,
  "high": 81.39901496470166,
  "lower_in": 14,
  "of": 16
 }
};
