import json
import math
import re
from pathlib import Path
from time import perf_counter_ns


EPSILON = 1e-9
REPEATS = 10
JSON_SIZES = (5, 13, 25)
DATA_PATH = Path(__file__).resolve().with_name("data.json")

CROSS_3 = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
X_3 = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]


def mac(pattern, kernel):
    size = len(pattern)
    score = 0.0
    for row in range(size):
        for col in range(size):
            score += pattern[row][col] * kernel[row][col]
    return score


def decide(score_a, score_b, label_a, label_b):
    if not math.isfinite(score_a) or not math.isfinite(score_b):
        raise ValueError("MAC 점수가 유한한 범위를 벗어났습니다.")
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b


def read_matrix(name):
    print("{} (3줄 입력, 공백 구분)".format(name))
    matrix = []
    while len(matrix) < 3:
        tokens = input("  {}/3행> ".format(len(matrix) + 1)).split()
        if len(tokens) == 3:
            try:
                row = [float(token) for token in tokens]
                if all(math.isfinite(value) for value in row):
                    matrix.append(row)
                    continue
            except ValueError:
                pass
        print("입력 형식 오류. 각 줄에 유한한 숫자 3개를 공백으로 구분해 입력하세요.")
    return matrix


def run_manual():
    filter_a = read_matrix("필터 A")
    filter_b = read_matrix("필터 B")
    print("필터 A와 B를 저장했습니다.")
    pattern = read_matrix("패턴")

    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    result = decide(score_a, score_b, "A", "B")
    print("\nA 점수:", score_a)
    print("B 점수:", score_b)
    if result == "UNDECIDED":
        print("판정: 판정 불가 (|A-B| < 1e-9)")
    else:
        print("판정:", result)
    print_benchmark([(3, pattern, filter_a)])

def print_benchmark(samples):
    print("\n성능 분석 (MAC 1회 호출 시간의 평균 / {}회)".format(REPEATS))
    print("{:>8}  {:>14}  {:>12}".format("크기", "평균 시간(ms)", "연산 횟수(N²)"))
    for size, pattern, kernel in samples:
        elapsed_ns = 0
        for _ in range(REPEATS):
            start = perf_counter_ns()
            mac(pattern, kernel)
            elapsed_ns += perf_counter_ns() - start
        mean_ms = elapsed_ns / REPEATS / 1_000_000
        dimensions = "{}×{}".format(size, size)
        print("{:>8}  {:>14.6f}  {:>12}".format(dimensions, mean_ms, size * size))

def normalize_label(raw):
    if isinstance(raw, str):
        label = raw.strip().lower()
        if label in ("+", "cross"):
            return "Cross"
        if label == "x":
            return "X"
    raise ValueError("지원하지 않는 라벨 {!r}".format(raw))


def validate_matrix(value, size, name):
    if not isinstance(value, list) or len(value) != size:
        raise ValueError("{}의 행 개수가 {}개여야 합니다.".format(name, size))
    for row_number, row in enumerate(value, start=1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("{}의 {}행은 열이 {}개여야 합니다.".format(name, row_number, size))
        for column_number, cell in enumerate(row, start=1):
            if (
                type(cell) not in (int, float)
                or not math.isfinite(cell)
            ):
                raise ValueError(
                    "{}의 {}행 {}열에 유한한 숫자가 필요합니다.".format(
                        name, row_number, column_number
                    )
                )
    return value


def load_filters(raw_filters):
    loaded = {}
    errors = {}
    for size in JSON_SIZES:
        key = "size_{}".format(size)
        try:
            if not isinstance(raw_filters, dict):
                raise ValueError("filters는 JSON 객체여야 합니다.")
            group = raw_filters.get(key)
            if not isinstance(group, dict):
                raise ValueError("{} 필터 객체가 없습니다.".format(key))

            normalized = {}
            for raw_label, matrix in group.items():
                label = normalize_label(raw_label)
                if label in normalized:
                    raise ValueError("{} 필터가 중복됩니다.".format(label))
                normalized[label] = validate_matrix(matrix, size, "{} {}".format(key, label))
            if normalized.keys() != {"Cross", "X"}:
                raise ValueError("Cross와 X 필터가 모두 필요합니다.")
        except (ValueError, OverflowError) as error:
            errors[size] = str(error)
            print("{} 필터 오류: {}".format(key, error))
        else:
            loaded[size] = normalized
            print("{} 필터 로드 완료 (Cross, X)".format(key))
    return loaded, errors

def analyze_case(key, case, filters, filter_errors):
    match = re.fullmatch(r"size_([1-9][0-9]*)_([0-9]+)", key)
    if match is None:
        raise ValueError("케이스 키는 size_{N}_{idx} 형식이어야 합니다.")

    size = int(match.group(1))
    if size not in JSON_SIZES:
        raise ValueError("지원하지 않는 크기 {}입니다.".format(size))
    if not isinstance(case, dict):
        raise ValueError("케이스는 input과 expected를 가진 JSON 객체여야 합니다.")
    if "input" not in case or "expected" not in case:
        raise ValueError("input과 expected가 모두 필요합니다.")
    if size in filter_errors:
        raise ValueError("필터 오류: " + filter_errors[size])

    pattern = validate_matrix(case["input"], size, "input")
    expected = normalize_label(case["expected"])
    score_cross = mac(pattern, filters[size]["Cross"])
    score_x = mac(pattern, filters[size]["X"])
    result = decide(score_cross, score_x, "Cross", "X")
    print("Cross 점수: {} | X 점수: {}".format(score_cross, score_x))
    print("판정: {} | expected: {}".format(result, expected))

    if result == expected:
        return None
    if result == "UNDECIDED":
        return "점수 차가 epsilon 미만이므로 UNDECIDED"
    return "예상 {} / 실제 {}".format(expected, result)


def run_json(path):
    try:
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
        if not isinstance(data, dict) or not isinstance(data.get("patterns"), dict):
            raise ValueError("최상위 JSON에 patterns 객체가 필요합니다.")
    except (OSError, ValueError) as error:
        print("JSON 읽기 오류: {}".format(error))
        return

    print("\n[1] 필터 로드")
    filters, filter_errors = load_filters(data.get("filters"))

    print("\n[2] 패턴 분석")
    failures = []
    for key, case in data["patterns"].items():
        print("\n--- {} ---".format(key))
        try:
            reason = analyze_case(key, case, filters, filter_errors)
        except (ValueError, OverflowError) as error:
            reason = str(error)
        if reason is None:
            print("PASS")
        else:
            print("FAIL ({})".format(reason))
            failures.append((key, reason))

    print("\n[3] 크기별 성능")
    samples = [(3, X_3, CROSS_3)]
    for size in JSON_SIZES:
        # 필터 오류가 있어도 해당 크기의 MAC 성능을 측정한다.
        sample = [[1.0] * size for _ in range(size)]
        samples.append((size, sample, sample))
    print_benchmark(samples)

    total = len(data["patterns"])
    print("\n[4] 결과 요약")
    print("총 테스트: {}개 | 통과: {}개 | 실패: {}개".format(
        total, total - len(failures), len(failures)
    ))
    if failures:
        print("실패 케이스")
        for key, reason in failures:
            print("- {}: {}".format(key, reason))


def main():
    print("=== Mini NPU Simulator ===")
    print("1. 사용자 입력 (3×3)")
    print("2. data.json 분석")
    try:
        while True:
            choice = input("선택: ").strip()
            if choice == "1":
                run_manual()
                return
            if choice == "2":
                run_json(DATA_PATH)
                return
            print("1 또는 2를 입력하세요.")
    except (EOFError, KeyboardInterrupt):
        print("\n입력을 취소했습니다.")
    except ValueError as error:
        print("판정 오류: {}".format(error))


if __name__ == "__main__":
    main()