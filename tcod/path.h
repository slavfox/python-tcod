#ifndef PYTHON_TCOD_PATH_H_
#define PYTHON_TCOD_PATH_H_

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "../libtcod/src/libtcod/pathfinder_frontier.h"

#ifdef __cplusplus
extern "C" {
#endif
/**
 *  Common NumPy data types.
 */
enum NP_Type {
  np_undefined = 0,
  np_int8,
  np_int16,
  np_int32,
  np_int64,
  np_uint8,
  np_uint16,
  np_uint32,
  np_uint64,
  np_float16,
  np_float32,
  np_float64,
};
/**
 *  A simple 4D NumPy array ctype.
 */
struct NArray {
  enum NP_Type type;
  int8_t ndim;
  char *data;
  ptrdiff_t shape[5]; // TCOD_PATHFINDER_MAX_DIMENSIONS + 1
  ptrdiff_t strides[5]; // TCOD_PATHFINDER_MAX_DIMENSIONS + 1
};

struct PathfinderRule {
  /** Rule condition, could be uninitialized zeros. */
  struct NArray condition;
  /** Edge cost map, required. */
  struct NArray cost;
  /** Number of edge rules in `edge_array`. */
  int edge_count;
  /** Example of 2D edges: [i, j, cost, i_2, j_2, cost_2, ...] */
  int* edge_array;
};

struct PathfinderHeuristic {
  int cardinal;
  int diagonal;
  int z;
  int w;
  int target[TCOD_PATHFINDER_MAX_DIMENSIONS];
};

struct PathCostArray {
    char *array;
    long long strides[2];
};

float PathCostArrayFloat32(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

float PathCostArrayUInt8(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

float PathCostArrayUInt16(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

float PathCostArrayUInt32(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

float PathCostArrayInt8(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

float PathCostArrayInt16(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

float PathCostArrayInt32(
    int x1, int y1, int x2, int y2, const struct PathCostArray *map);

/**
    Return the value to add to the distance to sort nodes by A*.

    `heuristic` can be NULL.

    `index[ndim]` must not be NULL.
 */
int compute_heuristic(
    const struct PathfinderHeuristic* heuristic, int ndim, const int* index);
int dijkstra2d(
    struct NArray* dist,
    const struct NArray* cost,
    int edges_2d_n,
    const int* edges_2d);

int dijkstra2d_basic(
    struct NArray* dist,
    const struct NArray* cost,
    int cardinal,
    int diagonal);

int hillclimb2d(
    const struct NArray* dist_array,
    int start_i,
    int start_j,
    int edges_2d_n,
    const int* edges_2d,
    int* out);

int hillclimb2d_basic(
    const struct NArray* dist,
    int x,
    int y,
    bool cardinal,
    bool diagonal,
    int* out);

int path_compute_step(
    struct TCOD_Frontier* frontier,
    struct NArray* dist_map,
    struct NArray* travel_map,
    int n,
    const struct PathfinderRule* rules, // rules[n]
    const struct PathfinderHeuristic* heuristic);

int path_compute(
    struct TCOD_Frontier* frontier,
    struct NArray* dist_map,
    struct NArray* travel_map,
    int n,
    const struct PathfinderRule* rules, // rules[n]
    const struct PathfinderHeuristic* heuristic);
/**
    Find and get a path along `travel_map`.

    Returns the length of the path, `out` must be NULL or `out[n*ndim]`.
    Where `n` is the value return from a previous call with the same
    parameters.
 */
size_t get_travel_path(
    int8_t ndim, const struct NArray* travel_map, const int* start, int* out);
#ifdef __cplusplus
}
#endif

#endif /* PYTHON_TCOD_PATH_H_ */
