export type ReservingResult = {
  latest_diagonal: number[];
  age_to_age_factors: number[];
  cumulative_development_factors: number[];
  ultimate_by_origin: number[];
  ibnr_by_origin: number[];
  total_latest: number;
  total_ultimate: number;
  total_ibnr: number;
};

export type DemoRun = {
  id: string;
  method: string;
  result: ReservingResult;
  originPeriods: string[];
  developmentPeriods: string[];
};

export const demoRun: DemoRun = {
  id: "run_preview",
  method: "chain_ladder",
  originPeriods: ["2020", "2021", "2022", "2023", "2024"],
  developmentPeriods: ["12", "24", "36", "48", "60"],
  result: {
    latest_diagonal: [2475, 2550, 2490, 2240, 1620],
    age_to_age_factors: [1.479091, 1.194232, 1.087912, 1.03125],
    cumulative_development_factors: [1.981716, 1.33982, 1.121909, 1.03125, 1],
    ultimate_by_origin: [2475, 2629.69, 2793.55, 3001.2, 3210.38],
    ibnr_by_origin: [0, 79.69, 303.55, 761.2, 1590.38],
    total_latest: 11375,
    total_ultimate: 14109.82,
    total_ibnr: 2734.82
  }
};
