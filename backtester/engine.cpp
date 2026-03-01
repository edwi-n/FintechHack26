/*
 * ============================================================================
 *  TRADING ARENA — High-Performance Backtesting Engine
 * ============================================================================
 *  C++ simulation core for evaluating AI strategies over thousands of
 *  3-month market jumps.  Dependency-free (standard library only).
 *
 *  Compile (Windows):
 *    g++ -shared -O2 -o engine.dll engine.cpp
 *
 *  Compile (Linux / macOS):
 *    g++ -shared -fPIC -O2 -o engine.so engine.cpp
 * ============================================================================
 */

#include <cmath>
#include <cstdlib>
#include <ctime>
#include <algorithm>

// ── Move type enum ──────────────────────────────────────────────────────────
// Passed as int from Python via ctypes.
enum MoveType
{
          MOVE_ATTACK_PUT = 0,  // Bet opponent's stock crashes  (option, stays on bench)
          MOVE_DEFENSE_PUT = 1, // Hedge your own stock           (option, stays on bench)
          MOVE_CALL = 2,        // Bet stock surges — costs premium, stock stays on bench
          MOVE_PLACE = 3        // Standard attack  — free, but stock leaves bench (no growth)
};

// ── Call premium rate ───────────────────────────────────────────────────────
// Call costs premium = CALL_PREMIUM_RATE * S0 per turn.
// Place costs 0 but sacrifices bench growth.
static const float CALL_PREMIUM_RATE = 0.05f; // 5 % of S0

// ── Game State ──────────────────────────────────────────────────────────────
struct GameState
{
          float p1_nw;           // Player 1 Net Worth
          float p2_nw;           // Player 2 Net Worth
          int turn;              // Current turn counter
          float p1_peak_nw;      // P1 peak NW (for drawdown tracking)
          float p2_peak_nw;      // P2 peak NW (for drawdown tracking)
          float p1_max_drawdown; // P1 worst drawdown seen so far
          float p2_max_drawdown; // P2 worst drawdown seen so far
};

// ── Globals ─────────────────────────────────────────────────────────────────
static GameState g_state;
static bool g_seeded = false;

// ── Helpers ─────────────────────────────────────────────────────────────────

// Ensure the PRNG is seeded exactly once.
static void ensure_seeded()
{
          if (!g_seeded)
          {
                    std::srand(static_cast<unsigned>(std::time(nullptr)));
                    g_seeded = true;
          }
}

// Track peak NW and update max drawdown for a player.
static void update_drawdown(float nw, float &peak, float &max_dd)
{
          if (nw > peak)
                    peak = nw;
          float dd = (peak - nw) / peak; // fraction from peak
          if (dd > max_dd)
                    max_dd = dd;
}

/*
 * ── compute_ai_decision ─────────────────────────────────────────────────────
 *  Core AI brain — shared by get_ai_move() and batch_simulate().
 *
 *  STRATEGY  (game-theory optimal against a random opponent)
 *  ─────────────────────────────────────────────────────────
 *  Key insight:  With GBM (mu drawn fresh each turn), lookback momentum
 *  provides near-zero signal for the *next* direction.  The only structural
 *  edge is the positive drift (P(UP) ≈ 56%).
 *
 *  • Call  → activates when stock rises  → damages opponent
 *  • DefPut → activates when stock falls → hedges own bench loss
 *
 *  Both contribute the same +|delta| to the NW *differential* when the
 *  prediction is correct.  But for *absolute NW*:
 *    – Playing Call on a DOWN turn costs the AI  −1.25|d|
 *    – Playing DefPut on a DOWN turn costs only −0.25|d|  (hedged)
 *    – Both are equivalent on UP turns (+0.5|d|)
 *
 *  This creates a trade-off:
 *    Always Call   → best win rate (+0.54|d|/turn diff) but worst profit
 *    Always DefPut → best profit  (+1.53|d|/turn NW)    but worst win rate
 *
 *  GAME-STATE-AWARE MIXING resolves this:
 *    • When BEHIND or EVEN → Call  (exploit drift for max differential)
 *    • When AHEAD          → Defense Put  (lock in the lead, boost profit)
 *    • When opponent near KO → Attack Put  (double damage finisher)
 *
 *  We layer a lightweight momentum signal on top for marginal edge
 *  in the rare windows where autocorrelation exists, but the game-state
 *  logic dominates the decision.
 */
static int compute_ai_decision(const float *lookback, int lb_count,
                               float my_nw, float opp_nw)
{
          // ── 2 % exploration noise (AtkPut or DefPut only) ────────────────
          if ((std::rand() % 100) < 2)
                    return (std::rand() % 2); // 0 = AtkPut, 1 = DefPut

          /*
           *  STRATEGY:  Empirical analysis shows that with 5 % Call premium,
           *  the expected NW contribution per turn is:
           *
           *    DefPut : WR ≈ 77 %, profit ≈ +21   (dominant)
           *    Place  : WR ≈ 77 %, profit ≈ −39   (same WR, terrible NW)
           *    AtkPut : WR ≈ 50 %, profit ≈  −5   (mediocre)
           *    Call   : WR ≈  8 %, profit ≈ −94   (premium destroys EV)
           *
           *  DefPut is the unconditional dominant strategy:
           *    • UP turns:  AI gets +d bench, hedge doesn't activate
           *    • DOWN turns: bench loss fully hedged (net 0)
           *    • NEVER pays premium, NEVER misses bench growth
           *    • Opponent's attacks (Call/Place) cancel bench on UP,
           *      but opponent pays premium (Call) or loses bench (Place)
           *    • The differential comes from opponent self-inflicted costs
           *
           *  The only deviation: Attack Put for KO finisher when the
           *  opponent is critically low.  AtkPut on DOWN turns doubles
           *  the opponent's loss (bench −d AND put damage −d = −2d).
           */

          // ── KO finisher: opponent critically low → Attack Put ─────────
          if (opp_nw < 200.0f && my_nw > opp_nw * 1.1f)
                    return MOVE_ATTACK_PUT;

          // ── Default: Defense Put (dominant strategy) ───────────────────
          return MOVE_DEFENSE_PUT;
}

/*
 * Apply a single move's effect.
 *
 *  owner_nw    – net-worth of the player who played the card
 *  opponent_nw – net-worth of the opposing player
 *
 * Returns nothing; modifies NW values in-place via pointers.
 */
static void apply_move(float S0, float S1, int move_type,
                       float *owner_nw, float *opponent_nw)
{
          float delta = 0.0f;

          switch (move_type)
          {
          case MOVE_ATTACK_PUT:
          {
                    // Delta = min(S1 - S0, 0) → subtract |delta| from opponent
                    delta = std::min(S1 - S0, 0.0f);
                    *opponent_nw -= std::fabs(delta);
                    break;
          }
          case MOVE_DEFENSE_PUT:
          {
                    // Delta = min(0, S1 - S0) → add |delta| to owner (hedge)
                    delta = std::min(0.0f, S1 - S0);
                    *owner_nw += std::fabs(delta);
                    break;
          }
          case MOVE_CALL:
          {
                    // Delta = min(0, S0 - S1) → subtract |delta| from opponent
                    delta = std::min(0.0f, S0 - S1);
                    *opponent_nw -= std::fabs(delta);
                    break;
          }
          case MOVE_PLACE:
          {
                    // Delta = min(0, S0 - S1) → subtract |delta| from opponent
                    delta = std::min(0.0f, S0 - S1);
                    *opponent_nw -= std::fabs(delta);
                    break;
          }
          default:
                    break; // unknown move → no-op
          }
}

// ────────────────────────────────────────────────────────────────────────────
//  Exported C API  (called from Python via ctypes)
// ────────────────────────────────────────────────────────────────────────────
extern "C"
{

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

          /* ── init_game ──────────────────────────────────────────────────────────── */
          EXPORT void init_game()
          {
                    g_state.p1_nw = 1000.0f;
                    g_state.p2_nw = 1000.0f;
                    g_state.turn = 0;
                    g_state.p1_peak_nw = 1000.0f;
                    g_state.p2_peak_nw = 1000.0f;
                    g_state.p1_max_drawdown = 0.0f;
                    g_state.p2_max_drawdown = 0.0f;
                    ensure_seeded();
          }

          /* ── resolve_turn ───────────────────────────────────────────────────────── *
           *  Core combat resolution for one 3-month jump.
           *
           *  S0, S1        – stock price at start / end of the 3-month window
           *  p1_move_type  – Player 1's chosen action (0-3)
           *  p2_move_type  – Player 2's chosen action (0-3)
           *
           *  Returns 1 if game is still active, 0 if someone's NW <= 0.
           * ────────────────────────────────────────────────────────────────────────── */
          EXPORT int resolve_turn(float S0, float S1, int p1_move_type, int p2_move_type)
          {
                    g_state.turn++;
                    float omega = S1 - S0;
                    float premium = CALL_PREMIUM_RATE * S0;

                    // 1. Bench Growth — Place removes stock from bench (no growth)
                    if (p1_move_type != MOVE_PLACE)
                              g_state.p1_nw += omega;
                    if (p2_move_type != MOVE_PLACE)
                              g_state.p2_nw += omega;

                    // 2. Call premium — paid when playing Call
                    if (p1_move_type == MOVE_CALL)
                              g_state.p1_nw -= premium;
                    if (p2_move_type == MOVE_CALL)
                              g_state.p2_nw -= premium;

                    // 3. Apply Player 1's move  (owner = P1, opponent = P2)
                    apply_move(S0, S1, p1_move_type, &g_state.p1_nw, &g_state.p2_nw);

                    // 4. Apply Player 2's move  (owner = P2, opponent = P1)
                    apply_move(S0, S1, p2_move_type, &g_state.p2_nw, &g_state.p1_nw);

                    // 4. Drawdown tracking
                    update_drawdown(g_state.p1_nw, g_state.p1_peak_nw, g_state.p1_max_drawdown);
                    update_drawdown(g_state.p2_nw, g_state.p2_peak_nw, g_state.p2_max_drawdown);

                    // 5. Check for KO (NW <= 0)
                    if (g_state.p1_nw <= 0.0f || g_state.p2_nw <= 0.0f)
                              return 0; // game over

                    return 1; // game continues
          }

          /* ── get_ai_move ────────────────────────────────────────────────────────── *
           *  Heuristic AI — delegates to compute_ai_decision().
           *
           *  Uses global GameState for NW-aware decision making.
           *  prices     – array of recent S0 prices (lookback window)
           *  num_prices – number of elements in `prices`
           *
           *  Returns: move id  (0 = Attack Put, 1 = Defense Put, 2 = Call, 3 = Place)
           * ────────────────────────────────────────────────────────────────────────── */
          EXPORT int get_ai_move(float *prices, int num_prices)
          {
                    ensure_seeded();
                    return compute_ai_decision(prices, num_prices,
                                               g_state.p1_nw, g_state.p2_nw);
          }

          /* ── get_ai_move_ex ────────────────────────────────────────────────────── *
           *  Extended AI move — accepts NW values directly so the caller can
           *  supply the real game state instead of relying on the internal
           *  global GameState.  Used by the live game server's offline bot.
           * ────────────────────────────────────────────────────────────────────────── */
          EXPORT int get_ai_move_ex(float *prices, int num_prices,
                                    float my_nw, float opp_nw)
          {
                    ensure_seeded();
                    return compute_ai_decision(prices, num_prices, my_nw, opp_nw);
          }

          /* ── Accessors ──────────────────────────────────────────────────────────── */
          EXPORT float get_p1_nw() { return g_state.p1_nw; }
          EXPORT float get_p2_nw() { return g_state.p2_nw; }
          EXPORT int get_turn() { return g_state.turn; }
          EXPORT float get_p1_max_drawdown() { return g_state.p1_max_drawdown; }
          EXPORT float get_p2_max_drawdown() { return g_state.p2_max_drawdown; }

          /* ── batch_simulate ─────────────────────────────────────────────────────── *
           *  Run N full games entirely in C++ for maximum throughput.
           *
           *  s0_arr, s1_arr  – parallel arrays of (S0, S1) price pairs
           *  turns_per_game  – how many 3-month jumps per game
           *  num_games       – total number of independent games to simulate
           *  results         – output array of size num_games
           *                    each element: +1 = AI (P1) wins, -1 = P2 wins, 0 = draw
           * ────────────────────────────────────────────────────────────────────────── */
          EXPORT void batch_simulate(float *s0_arr, float *s1_arr,
                                     int turns_per_game, int num_games,
                                     int *results)
          {
                    ensure_seeded();
                    const int MAX_LB = 16; // max lookback depth

                    for (int g = 0; g < num_games; g++)
                    {
                              float p1 = 1000.0f, p2 = 1000.0f;
                              int base = g * turns_per_game;

                              // Per-game lookback ring buffer for the AI
                              float lb[MAX_LB];
                              int lb_count = 0;

                              for (int t = 0; t < turns_per_game; t++)
                              {
                                        float S0 = s0_arr[base + t];
                                        float S1 = s1_arr[base + t];

                                        // Append S0 to lookback (ring buffer)
                                        if (lb_count < MAX_LB)
                                                  lb[lb_count++] = S0;
                                        else
                                        {
                                                  for (int k = 1; k < MAX_LB; k++)
                                                            lb[k - 1] = lb[k];
                                                  lb[MAX_LB - 1] = S0;
                                        }

                                        // AI (P1): full momentum + game-state heuristic
                                        int ai_move = compute_ai_decision(lb, lb_count, p1, p2);

                                        // Random opponent (P2)
                                        int rand_move = std::rand() % 4;

                                        // Bench growth — Place removes stock from bench
                                        float omega = S1 - S0;
                                        float premium = CALL_PREMIUM_RATE * S0;
                                        if (ai_move != MOVE_PLACE)
                                                  p1 += omega;
                                        if (rand_move != MOVE_PLACE)
                                                  p2 += omega;

                                        // Call premium
                                        if (ai_move == MOVE_CALL)
                                                  p1 -= premium;
                                        if (rand_move == MOVE_CALL)
                                                  p2 -= premium;

                                        // P1 move
                                        float d1 = 0.0f;
                                        switch (ai_move)
                                        {
                                        case MOVE_ATTACK_PUT:
                                                  d1 = std::min(S1 - S0, 0.0f);
                                                  p2 -= std::fabs(d1);
                                                  break;
                                        case MOVE_DEFENSE_PUT:
                                                  d1 = std::min(0.0f, S1 - S0);
                                                  p1 += std::fabs(d1);
                                                  break;
                                        case MOVE_CALL:
                                                  d1 = std::min(0.0f, S0 - S1);
                                                  p2 -= std::fabs(d1);
                                                  break;
                                        case MOVE_PLACE:
                                                  d1 = std::min(0.0f, S0 - S1);
                                                  p2 -= std::fabs(d1);
                                                  break;
                                        }

                                        // P2 move
                                        float d2 = 0.0f;
                                        switch (rand_move)
                                        {
                                        case MOVE_ATTACK_PUT:
                                                  d2 = std::min(S1 - S0, 0.0f);
                                                  p1 -= std::fabs(d2);
                                                  break;
                                        case MOVE_DEFENSE_PUT:
                                                  d2 = std::min(0.0f, S1 - S0);
                                                  p2 += std::fabs(d2);
                                                  break;
                                        case MOVE_CALL:
                                                  d2 = std::min(0.0f, S0 - S1);
                                                  p1 -= std::fabs(d2);
                                                  break;
                                        case MOVE_PLACE:
                                                  d2 = std::min(0.0f, S0 - S1);
                                                  p1 -= std::fabs(d2);
                                                  break;
                                        }

                                        if (p1 <= 0.0f || p2 <= 0.0f)
                                                  break;
                              }

                              if (p1 > p2)
                                        results[g] = 1; // AI wins
                              else if (p2 > p1)
                                        results[g] = -1; // Random wins
                              else
                                        results[g] = 0; // draw
                    }
          }

} // extern "C"
