# Mini NPU 시뮬레이터 따라 만들기

3×3 입력부터 JSON 일괄 판정까지, `main.py` 한 파일을 단계별로 완성한다. 각 단계의 **따라 칠 코드**를 파일 아래에 순서대로 추가하고, 터미널에서 확인 명령을 실행한다. Python 3.8 이상과 표준 라이브러리만 사용한다.

| 단계 | 작성할 기능 | 확인할 결과 |
|---|---|---|
| 1 | MAC 점수와 epsilon 비교 | X 패턴의 점수 1, 5와 근소한 동점 |
| 2 | 3×3 콘솔 입력과 검증 | 잘못된 행을 다시 입력하고 B 판정 |
| 3 | 반복 시간 측정 | 3×3 평균 시간과 9 MAC |
| 4 | JSON 스키마 검증과 일괄 판정 | 케이스별 PASS/FAIL과 총계 |
| 5 | 실행 메뉴 연결 | `python3 main.py`로 두 모드 실행 |
| 6 | 오류 재현과 제출 README 작성 | 실제 측정값과 실패 원인 기록 |

## 준비

작업공간 터미널에서 다음을 실행한다. 편집기에서 `mac_simul/main.py`를 새로 연다.

```sh
cd mac_simul
python3 --version
touch main.py
```

| 파일 | 역할 |
|---|---|
| `main.py` | 이 가이드를 따라 직접 작성하는 실행 파일 |
| `data.json` | 제공받은 과제 데이터 또는 4단계에서 생성하는 실습 데이터 |
| `README.md` | 6단계에서 작성하는 제출 리포트 |

## 1. 같은 위치끼리 곱하고 더하기

`pattern[row][col]`로 행과 열을 지정한다. 이중 반복문이 각 칸을 한 번 방문하고, 두 값의 곱을 `score`에 더한다. 아래 MAC 함수는 호출 전에 두 배열의 크기가 검증됐다고 가정한다. 비교 함수는 점수 차이의 절댓값이 `1e-9` 미만이면 `UNDECIDED`를 반환한다. 차이가 epsilon과 같을 때는 점수가 큰 쪽이 이긴다.

### 따라 칠 코드

```python
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
```

### 중간 확인

```sh
python3 -c 'from main import CROSS_3, X_3, mac, decide; a = mac(X_3, CROSS_3); b = mac(X_3, X_3); print(a, b, decide(a, b, "A", "B")); print(decide(0.1 + 0.2, 0.3, "A", "B"))'
```

첫 줄은 `1.0 5.0 B`, 둘째 줄은 `UNDECIDED`다. X 패턴과 십자가 필터는 가운데 칸만 겹친다. 이 MAC 점수는 겹친 위치의 가중합이므로, 임의의 숫자 필터에서는 값이 큰 칸이나 필터의 전체 크기가 점수에 영향을 줄 수 있다.

## 2. 3×3 콘솔 입력 받기

한 행에 숫자 세 개를 받고, 형식이 맞을 때만 저장한다. 첫 번째 행을 잘못 입력하면 첫 번째 행을 다시 묻는다. 세 행이 모여야 다음 행렬로 넘어간다. `nan`, `inf` 등은 비교에 사용할 수 없으므로 입력 시 거른다.

### 따라 칠 코드

```python
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
```

### 중간 확인

```sh
python3 -c 'from main import run_manual; run_manual()'
```

처음에 `0 1`을 입력해 첫 행을 다시 묻는지 확인한다. 이어 아래 표에서 **입력 줄**을 위에서부터 한 줄씩 입력한다.

| 대상 | 입력 줄 |
|---|---|
| 필터 A | `0 1 0` → `1 1 1` → `0 1 0` |
| 필터 B | `1 0 1` → `0 1 0` → `1 0 1` |
| 패턴 | `1 0 1` → `0 1 0` → `1 0 1` |

점수는 A가 `1.0`, B가 `5.0`이고 판정은 `B`다. 두 필터에 같은 행렬을 넣어 한 번 더 실행하면 `판정 불가`가 출력된다.

## 3. MAC 연산 시간 측정하기

`perf_counter_ns()`로 한 번의 `mac()` 함수 호출 전후를 재고 10회 평균을 계산한다. 나노초를 밀리초로 바꾸려면 `1_000_000`으로 나눈다. 표의 연산 횟수는 **필터 한 개에 대한 MAC 호출 1회** 기준으로 N²이다. 두 필터를 비교할 때는 2N²개의 위치에서 MAC을 수행한다.

### 따라 칠 코드

```python
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
```

그다음 `run_manual()`의 마지막에 아래 **한 줄**을 추가한다. 함수 안에서 `if/else` 블록과 같은 들여쓰기(공백 네 칸)를 사용한다.

```python
    print_benchmark([(3, pattern, filter_a)])
```

### 중간 확인

```sh
python3 -c 'from main import CROSS_3, X_3, print_benchmark; print_benchmark([(3, X_3, CROSS_3)])'
```

3×3 한 행에 ms 단위의 평균 시간과 연산 횟수 `9`가 표시된다. 시간값은 실행 환경에 따라 달라진다.

## 4. JSON 데이터 검증하고 일괄 판정하기

`filters.size_5.cross`처럼 크기별 필터를 찾고, `patterns.size_5_1`의 키에서 추출한 크기 5와 연결한다. 행과 열이 모두 5개인지 확인한 뒤 MAC을 호출한다. 기대 라벨과 필터 키는 같은 함수로 `Cross` 또는 `X`로 변환한다.

| JSON 입력 | 변환 또는 처리 |
|---|---|
| `expected`의 `+`, 필터 키 `cross` | `Cross` |
| `expected` 또는 필터 키의 `x` | `X` |
| `Cross`, `X` 같은 표준 라벨 | 같은 표준 라벨로 변환 |
| 지원하지 않는 라벨·크기, 배열 차원 오류 | 해당 케이스 FAIL |
| 한 크기의 필터 파일 항목에 오류 | 그 크기를 사용하는 케이스만 FAIL |
| 파일 없음, 손상된 JSON, `patterns` 객체 없음 | 읽기 오류 메시지를 출력하고 모드 종료 |

### 4-1. JSON 검증 함수 추가

```python
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
```

`type(cell)`을 확인하므로 JSON의 `true`·`false`와 `"1"`은 숫자로 처리되지 않는다. 필터를 읽는 중 오류가 나면 크기별로 이유를 저장해, 나중에 해당 필터를 사용하는 패턴에 붙인다.

### 4-2. 케이스 판정과 요약 추가

```python
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
```

JSON 모드 성능 표는 3×3 예제와 5×5·13×13·25×25의 합성 행렬을 사용한다. 개별 필터나 케이스에 오류가 있어도, 파일과 patterns 객체를 읽을 수 있으면 네 크기를 같은 측정 횟수로 비교할 수 있다. FAIL 사유를 반환한 케이스와 검증에서 예외가 난 케이스 모두 같은 실패 목록에 기록된다.

### 4-3. 실습용 data.json 만들기

과제용 `data.json`이 있으면 `main.py` 옆에 놓는다. 없다면 다음 명령을 **터미널**에 붙여 넣는다. 이 코드는 `main.py`에 넣지 않는다. 파일이 이미 있으면 생성을 건너뛴다.

아래 생성 코드는 정상 케이스 6개와 실패 예제 2개를 합쳐 총 8개를 만든다. 기존 `data.json`에 케이스가 6개만 있다면 실행 결과도 6개만 나온다. 가이드의 실패 예제까지 재현하려면 `mac_simul` 폴더에서 기존 파일을 먼저 백업한 뒤, 아래 생성 코드를 실행한다. 과제 데이터를 그대로 사용할 때는 백업·재생성할 필요 없이 실제 케이스 수와 결과를 기록한다.

```sh
mv data.json "data_backup_$(date +%Y%m%d_%H%M%S).json"
```

```sh
python3 - <<'PY'
import json
from pathlib import Path

path = Path("data.json")
data = {"filters": {}, "patterns": {}}
for size in (5, 13, 25):
    center = size // 2
    cross = [
        [int(row == center or col == center) for col in range(size)]
        for row in range(size)
    ]
    diagonal = [
        [int(row == col or row + col == size - 1) for col in range(size)]
        for row in range(size)
    ]
    data["filters"]["size_{}".format(size)] = {"cross": cross, "x": diagonal}
    data["patterns"]["size_{}_1".format(size)] = {"input": cross, "expected": "+"}
    data["patterns"]["size_{}_2".format(size)] = {"input": diagonal, "expected": "x"}

near_tie = [[0.0] * 13 for _ in range(13)]
near_tie[6][0] = 0.1
near_tie[6][1] = 0.2
near_tie[0][0] = 0.3
data["patterns"]["size_13_3"] = {"input": near_tie, "expected": "x"}
data["patterns"]["size_25_3"] = {"input": [[1]], "expected": "+"}

try:
    with path.open("x", encoding="utf-8") as output:
        json.dump(data, output, indent=2)
        output.write("\n")
except FileExistsError:
    print("기존 data.json을 사용합니다.")
else:
    print("실습용 data.json을 생성했습니다.")
PY
```

### 중간 확인

```sh
python3 -c 'from main import DATA_PATH, run_json; run_json(DATA_PATH)'
```

생성한 실습 데이터라면 총 8개 중 6개 PASS와 2개 FAIL이 나온다. 과제에서 별도로 받은 데이터의 결과는 내용에 따라 달라진다.

| 케이스 | Cross 점수 | X 점수 | 기대 결과 |
|---|---:|---:|---|
| `size_5_1` | 9.0 | 1.0 | Cross · PASS |
| `size_5_2` | 1.0 | 9.0 | X · PASS |
| `size_13_3` | 0.30000000000000004 | 0.3 | UNDECIDED · FAIL |
| `size_25_3` | — | — | 행 개수 오류 · FAIL |

## 5. 실행 메뉴 연결하기

아래 코드를 파일 맨 끝에 추가한다. `if __name__ == "__main__"` 덕분에 앞 단계처럼 함수를 가져올 때는 메뉴가 뜨지 않는다. 행 입력 중 EOF가 발생하면 취소 메시지가 나오고, 메뉴가 잘못되면 다시 선택할 수 있다.

### 따라 칠 코드

```python
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
```

### 최종 확인

```sh
python3 main.py
```

| 실행할 확인 | 기대 결과 |
|---|---|
| 메뉴에서 `9`를 입력한 뒤 `1` 입력 | 안내 후 모드 1 실행 |
| 모드 1에서 `0 1`, `0 0 0 0`, `0 abc 0`을 차례로 입력 | 세 입력 모두 거절하고 같은 행을 다시 요청 |
| 모드 1의 2단계 예제 입력 | A 1.0, B 5.0, B 판정, 3×3 성능 행 |
| 모드 1에서 A와 B에 동일한 행렬 입력 | 판정 불가 |
| 모드 2에서 4단계 실습 데이터 사용 | 8개 중 6 PASS, 2 FAIL 및 실패 이유 |
| 성능 표 확인 | 3×3, 5×5, 13×13, 25×25에서 각각 9, 25, 169, 625 MAC |
| 실습 데이터 복사본의 `size_25_3` 키를 `bad_key`로 바꿔 실행 | 변경한 케이스가 키 형식 오류로 FAIL. 다른 케이스는 정상 처리 |

마지막 키 형식 검증은 4-3에서 생성한 8개짜리 실습 데이터를 사용한다. `mac_simul` 폴더에서 다음 명령으로 `data_check.json` 복사본을 만들면서 `size_25_3` 키를 `bad_key`로 바꾼다. 원본 `data.json`은 유지한다. 기존 `data_check.json`이 있으면 덮어쓰지 않으므로, 다시 만들려면 기존 복사본을 먼저 다른 이름으로 옮긴다.

```sh
python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("data.json").read_text(encoding="utf-8"))
if "size_25_3" not in data["patterns"]:
    raise SystemExit("size_25_3이 없습니다. 4-3의 8개짜리 실습 데이터를 먼저 준비하세요.")
data["patterns"]["bad_key"] = data["patterns"].pop("size_25_3")
with Path("data_check.json").open("x", encoding="utf-8") as output:
    json.dump(data, output, ensure_ascii=False, indent=2)
    output.write("\n")
print("data_check.json을 생성했습니다.")
PY
```

복사본을 생성한 다음 아래 명령으로 실행한다. 이 실행 명령 자체는 파일을 만들지 않는다.

```sh
python3 -c 'from pathlib import Path; from main import run_json; run_json(Path("data_check.json"))'
```

`bad_key`가 키 형식 오류로 FAIL인지 확인한다. 총계는 원본과 같은 8개 중 6 PASS, 2 FAIL이지만, 해당 케이스의 실패 원인이 행 개수 오류에서 키 형식 오류로 바뀐다. `size_13_3`의 동점 FAIL과 나머지 정상 케이스의 결과는 동일하다.

## 6. 제출용 README.md 작성하기

아래 골격을 `README.md`에 옮긴다. 실제 데이터로 모드 2를 실행해 집계, 실패 목록, 시간값을 채운다. 실습용 데이터를 사용했으면 데이터 출처에 그렇게 적는다. 결과 리포트의 10개 항목에 각각 한 줄 이상 작성한다.

```markdown
# Mini NPU Simulator

## 실행 방법

- Python 버전과 운영체제
- 실행 명령 `python3 main.py`
- 모드 1 입력 방법과 모드 2의 data.json 위치

## 구현 요약

- 2차원 리스트와 이중 반복문을 사용한 MAC
- 필터 키와 기대 라벨을 Cross/X로 변환하는 방식
- 절대 점수 차이가 1e-9 미만이면 UNDECIDED로 판정

## 결과 리포트

1. 사용한 데이터와 총 테스트·통과·실패 수를 기록했다.
2. 실패한 케이스의 키와 콘솔에 나온 원인을 기록했다.
3. 키 형식, 라벨 또는 행렬 크기 문제를 확인한 방법을 적었다.
4. 정상 예제의 기대 점수와 실제 점수를 대조해 MAC을 확인했다.
5. epsilon 동점이 발생한 케이스의 두 점수와 차이를 기록했다.
6. 동점이 FAIL인 이유를 expected 라벨과 대조해 설명했다.
7. 크기별 MAC 평균 시간을 ms 단위로 표에 기록했다.
8. 이중 반복문은 각 행의 모든 열을 한 번씩 방문하므로 N²개의 MAC을 수행했다.
9. 25×25는 5×5보다 한 변이 5배 길고 MAC 수는 25배인 625회였다. 직접 측정한 평균 시간의 비율을 이 값과 비교했다.
10. 시간 측정은 각 크기에서 MAC 함수 호출만 10회 측정했다. 작은 입력에서는 타이머·함수 호출의 고정 비용이 시간 비율에 미칠 수 있는 영향을 적었다.
```

실습용 `size_13_3`은 `0.1 + 0.2`와 `0.3`의 차이가 약 `5.55e-17`이라 `UNDECIDED`가 된다. 기대 라벨은 `X`이므로 FAIL이다. `size_25_3`은 1×1 입력을 25×25 필터로 판정하려 했으므로 배열을 검증하는 단계에서 FAIL이다. 두 경우를 README에서 구분해 설명한다.

FAIL이 0개라면, 라벨 정규화 후 각 기대 라벨이 실제 판정과 일치했고 데이터의 키·크기 검증도 모두 통과했는지 결과를 근거로 적는다. `UNDECIDED`가 없었다면 각 점수 차가 epsilon 이상이었다는 뜻이다. 동점 처리는 1단계 또는 모드 1의 동일 필터 예제로 직접 확인해 기록할 수 있다.

### 보너스 확장

- 4단계 생성 코드를 `make_filters(size)` 함수로 옮겨 홀수 크기의 십자가와 X를 생성하고, 3×3 예제나 성능 측정에서 재사용한다.
- 2차원 배열을 행 순서대로 펼친 뒤 `range(size * size)`로 MAC을 구현한다. 같은 입력과 반복 횟수로 두 방식을 재고, 변환 시간을 포함한 경우와 제외한 경우를 구분해 기록한다. 두 방식 모두 시간 복잡도는 O(N²)다.
