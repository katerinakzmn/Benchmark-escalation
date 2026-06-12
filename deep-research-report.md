# Разработка бенчмарка задач для оценки политик эскалации в мультиагентной разработке сервисов

## Аннотация

Цель работы - разработать benchmark-среду для исследования политик эскалации в мультиагентной разработке программных сервисов. В отличие от классических benchmark для генерации кода, которые в основном отвечают на вопрос "получился ли правильный финальный патч", в данной работе оценивается процесс принятия решений: когда оставить задачу слабой модели, когда повторить попытку с измененным контекстом, когда перейти к более сильной модели, когда запустить тесты, когда подключить человека и когда остановиться.

Технологическим результатом семестра должен стать воспроизводимый прототип benchmark-escalation: набор задач, среда запуска, несколько baseline-политик, логирование траекторий, модуль метрик и отчетность по экспериментам. Главная особенность прототипа - сохранение не только финального результата, но и всей траектории решения в формате `state -> action -> next_state -> reward`, пригодном для сравнения правил эскалации и дальнейшего обучения политик.

## 1. Контекст и постановка задачи

Современные LLM-агенты могут решать задачи разработки: исправлять функции, модифицировать API, запускать тесты, анализировать ошибки и предлагать патчи. Однако практическая система разработки редко ограничивается одним вызовом модели. Чаще возникает последовательность решений:

1. дешевая или быстрая модель предлагает первое решение;
2. код проходит ревью или статическую проверку;
3. запускаются тесты;
4. при неудаче агент решает, что делать дальше:
   - повторить попытку той же моделью;
   - изменить prompt или добавить hint от reviewer/tester;
   - перейти на более сильную модель;
   - вызвать внешний инструмент;
   - передать задачу человеку;
   - остановиться из-за бюджета или отсутствия прогресса.

Такие решения образуют политику эскалации. Для ее оценки недостаточно знать только итоговый статус `solved / not solved`. Нужны данные о промежуточных состояниях, действиях и цене каждого действия.

### 1.1. Тема работы

**Разработка бенчмарка задач для оценки политик эскалации в мультиагентной разработке сервисов.**

### 1.2. Цель работы

Разработать воспроизводимый benchmark prototype, который позволяет сравнивать политики эскалации в мультиагентном процессе решения задач разработки по качеству, стоимости, числу попыток, числу тестовых запусков, частоте перехода к сильной модели и частоте обращения к человеку.

### 1.3. Задачи работы

1. Изучить существующие benchmark для генерации кода, исправления багов и агентной разработки.
2. Выделить ограничения этих benchmark с точки зрения оценки именно политики эскалации.
3. Проанализировать текущий прототип benchmark-escalation.
4. Сформулировать формат задач, логов и метрик, необходимых для оценки траекторий.
5. Спроектировать архитектуру benchmark-среды: dataset, environment, agents, backends, policies, runner, metrics.
6. Реализовать инкрементальный прототип:
   - toy dataset;
   - mock backend без обязательных API-ключей;
   - несколько baseline policies;
   - единый CLI;
   - сохранение артефактов прогонов;
   - расчет метрик.
7. Провести серию экспериментов и сравнить политики.
8. Подготовить README, технический отчет и рекомендации по развитию benchmark до real-repository задач.

## 2. Требования научного руководителя и как они учтены

На первой встрече была обозначена общая исследовательская идея: нужна система, которая изучает не только способность модели решить задачу, но и управленческое решение о переходе к другим способам решения. Для данной работы локальная технологическая задача - создать benchmark для тестирования такой системы.

Ниже перечислены ключевые замечания и то, как они отражены в проекте.

| Замечание / ожидание | Как учтено в работе |
|---|---|
| Сначала изучить существующие benchmark: SWE-bench, HumanEval и похожие | В разделе 3 приведен обзор benchmark и их ограничений |
| SWE-bench проверяет в основном финальный патч, а не шаги эскалации | В разделе 3.3 сформулирован разрыв: нужен trajectory-level benchmark |
| Нужно отслеживать, что сделала модель, когда сделала и какой получился результат | В разделе 7 задан формат событий и MDP-траекторий |
| Нужно понимать, когда и как эскалировать модель | В разделе 8 описаны baseline policies и oracle labels |
| Нужно измерять, сколько тестов не проходило изначально, что произошло после слабой/сильной модели, сколько тестов прошло после каждой попытки | В разделе 8 приведены метрики `initial_failures`, `pass_rate_delta`, `cost_to_green`, `missed_escalation`, `premature_escalation` |
| Нужен технологический результат, а не только теоретический обзор | В разделе 10 приведен полный технологический отчет: архитектура, файлы, CLI, данные, метрики, план реализации |

## 3. Обзор существующих benchmark

### 3.1. HumanEval и EvalPlus

HumanEval - benchmark для оценки синтеза небольших Python-функций. Каждая задача содержит prompt, имя entry point, canonical solution и набор unit tests. Основная метрика - functional correctness, обычно `pass@k`.

EvalPlus развивает эту идею: добавляет больше тестов к HumanEval и MBPP, чтобы уменьшить вероятность случайного прохождения слабым или неполным решением.

**Плюсы для данной работы:**

- простой формат задач;
- быстрый запуск;
- удобно использовать для toy-уровня;
- понятная метрика прохождения тестов.

**Минусы:**

- задачи слишком локальные;
- нет репозиторного контекста;
- нет multi-agent workflow;
- нет понятия стоимости, эскалации и траектории решений.

### 3.2. SWE-bench, SWE-bench Lite и SWE-bench Verified

SWE-bench - benchmark для оценки исправления реальных GitHub issues в Python-репозиториях. Для каждой задачи задается репозиторий, issue, окружение, тесты и ожидаемый патч. Оценка запускает тесты в воспроизводимой среде и проверяет, проходит ли патч.

SWE-bench Lite - облегченная подвыборка для более дешевых экспериментов. SWE-bench Verified - human-validated subset задач, которые были дополнительно проверены людьми на решаемость и корректность.

**Плюсы для данной работы:**

- реальные задачи из репозиториев;
- воспроизводимая инфраструктура;
- хороший ориентир для будущего stage с real-repository задачами;
- развитый harness с изоляцией окружений.

**Минусы:**

- стандартная оценка привязана к финальному патчу;
- benchmark не оценивает отдельно момент эскалации;
- дорого для массовых policy sweeps;
- Docker/harness может быть слишком тяжелым для первого прототипа.

### 3.3. BugsInPy и Defects4J

BugsInPy содержит реальные Python-баги с командами checkout, setup и test. Defects4J выполняет похожую роль для Java-экосистемы: предоставляет баги, метаданные и CLI для воспроизведения.

**Плюсы:**

- реальные баги;
- есть buggy/fixed revisions;
- можно использовать как источник задач следующего уровня сложности.

**Минусы:**

- это benchmark для исправления дефектов, а не для оценки policy control;
- нет встроенной модели действий `retry / escalate / call_human`;
- нет стандартного trajectory log.

### 3.4. DevBench и workflow-oriented benchmark

DevBench и близкие benchmark пытаются оценивать более широкий цикл разработки: design, setup, implementation, testing. Это ближе к идее multi-step agent workflow, чем HumanEval.

**Плюсы:**

- учитывается несколько стадий разработки;
- benchmark ближе к реальному software engineering процессу.

**Минусы:**

- policy escalation все равно не является центральным объектом оценки;
- обычно оценивается конечное выполнение стадии или задачи, а не оптимальность управленческих решений.

### 3.5. Сравнительная таблица

| Benchmark | Что измеряет | Формат | Основная метрика | Есть ли траектория `state/action/reward` | Полезность для benchmark-escalation |
|---|---|---|---|---|---|
| HumanEval | Генерация функции | prompt + tests | pass@k | Нет | Базовый формат toy-задач |
| EvalPlus | Более строгая генерация функции | prompt + расширенные tests | pass@k / pass rate | Нет | Идеи для усиления тестов |
| SWE-bench | Исправление GitHub issue | repo + issue + tests | resolved% | Нет в стандартной оценке | Будущий источник real tasks |
| SWE-bench Lite | Удешевленная версия SWE-bench | subset | resolved% | Нет | Возможный stage 3 |
| SWE-bench Verified | Проверенная подвыборка SWE-bench | human-validated subset | resolved% | Нет | Качественный future eval split |
| BugsInPy | Реальные Python-баги | buggy/fixed revisions | tests pass | Нет | Источник задач после toy stage |
| Defects4J | Реальные Java-баги | project revisions + CLI | tests pass | Нет | Референс воспроизводимости |
| DevBench | Workflow разработки | multi-stage tasks | stage/task success | Частично | Архитектурный ориентир |

### 3.6. Вывод из обзора

Главный пробел: существующие benchmark хорошо отвечают на вопрос "решена ли задача", но плохо отвечают на вопрос "правильно ли агент управлял процессом решения". Для политики эскалации важно оценивать:

- начальное состояние задачи;
- качество первой слабой попытки;
- изменение pass rate после каждой попытки;
- стоимость каждого действия;
- момент перехода на strong model;
- момент обращения к человеку;
- ошибки ранней и поздней эскалации;
- итоговую полезность политики при ограниченном бюджете.

Значит, benchmark-escalation должен быть не заменой SWE-bench/HumanEval, а дополнительным слоем, который превращает задачу разработки в эпизод принятия решений.

## 4. Аудит текущего прототипа benchmark-escalation

В текущем репозитории уже есть начальный прототип:

```text
agents/
  base.py
  developer.py
  manager.py
  reviewer.py
  tester.py
dataset/
  tasks.json
compute_oracle.py
environment.py
llm_client.py
mas_runner.py
tasks.py
```

### 4.1. Что уже реализовано

| Компонент | Файл | Текущее состояние |
|---|---|---|
| Dataset | `dataset/tasks.json` | 3 toy-задачи: `T001`, `T002`, `T003` |
| Loader | `tasks.py` | Загружает JSON и строит callable-тесты |
| Environment | `environment.py` | Запускает тесты и возвращает `StepResult` |
| Developer | `agents/developer.py` | Генерирует код через LLM client |
| Reviewer | `agents/reviewer.py` | Проверяет код и дает рекомендацию |
| Tester | `agents/tester.py` | Оборачивает `Environment.run()` в агентное сообщение |
| Manager | `agents/manager.py` | Принимает решения после generate/review/test |
| Runner | `mas_runner.py` | Запускает цикл `Developer -> Manager -> Reviewer -> Tester -> Manager` |
| Metrics | `mas_runner.py` | Считает outcome, iterations, pass rate, confidence, cost |
| Oracle draft | `compute_oracle.py` | Пытается вычислять oracle label для weak/strong |

### 4.2. Сильные стороны прототипа

1. Уже есть разделение ролей агентов.
2. Manager действительно принимает решения на нескольких фазах:
   - после генерации;
   - после ревью;
   - после тестов.
3. Есть цепочка эскалации `weak -> strong -> human`.
4. Есть первичные метрики стоимости и качества.
5. Есть toy dataset с задачами разной сложности.
6. Есть event-based trace, который можно нормализовать в MDP-траектории.

### 4.3. Критичные проблемы

| Проблема | Где | Почему важно | Приоритет |
|---|---|---|---|
| `compute_oracle.py` вызывает `env.run_all_tests(code)`, но в `Environment` есть только `run(code, model_used, step_number)` | `compute_oracle.py`, `environment.py` | Oracle script сейчас не запускается | P0 |
| Жесткая зависимость от `OPENAI_API_KEY` | `llm_client.py` | Benchmark нельзя массово запускать без внешнего API | P0 |
| Нет mock backend | `llm_client.py`, `agents/` | Невозможно дешево и воспроизводимо сравнивать политики | P0 |
| В коде и комментариях есть рассинхрон по провайдерам моделей | `llm_client.py`, `compute_oracle.py` | В одном месте OpenAI, в другом упоминается Gemini | P1 |
| Тесты выполняются через `exec` | `tasks.py` | Небезопасно и плохо масштабируется на real tasks | P1 |
| Политика зашита в `mas_runner.py` | `mas_runner.py` | Трудно сравнивать разные policies | P1 |
| Результаты пишутся в один файл в корне | `mas_runner.py` | Плохо для экспериментов и воспроизводимости | P1 |
| Нет CLI и YAML-конфигов | весь проект | Нельзя запускать sweep разных политик одной командой | P1 |
| Трассы event-based, но не MDP-based | `mas_runner.py` | Нельзя напрямую оценивать policy learning | P1 |

### 4.4. Минимальные исправления

#### Исправление oracle

В `compute_oracle.py` нужно заменить:

```python
result = env.run_all_tests(code)
```

на:

```python
result = env.run(
    code=code,
    model_used=tier.value,
    step_number=1,
)
```

Либо добавить thin-wrapper в `Environment`:

```python
def run_all_tests(self, code: str) -> StepResult:
    return self.run(code=code, model_used="unknown", step_number=0)
```

Для чистоты лучше использовать существующий `Environment.run()`, чтобы не плодить два API для одного действия.

#### Backend abstraction

Текущий `llm_client.py` должен стать адаптером, а не единственным способом генерации:

```text
backends/
  base.py
  mock_backend.py
  openai_backend.py
  gemini_backend.py
```

Агенты должны зависеть от интерфейса:

```python
class ChatBackend:
    def chat(self, model: str, system_prompt: str, user_prompt: str, **kwargs) -> str:
        ...
```

#### Run artifacts

Вместо перезаписи `mas_traces.json` в корне нужно сохранять каждый запуск:

```text
runs/
  run_2026_06_12_001/
    config.json
    events.json
    traces.json
    metrics.json
    summary.md
```

## 5. Целевая архитектура benchmark

### 5.1. Общая схема

```text
benchmark_escalation/
  agents/
    developer.py
    reviewer.py
    tester.py
    manager.py
  backends/
    base.py
    mock_backend.py
    openai_backend.py
    gemini_backend.py
  dataset/
    tasks.json
    oracle_labels.json
  cases/
    T001/
      issue.md
      solution.py
      test_solution.py
      metadata.yaml
      reference_solution.py
  environments/
    toy_environment.py
    pytest_environment.py
  policies/
    base.py
    fixed_weak.py
    fixed_strong.py
    retry_then_escalate.py
    confidence_threshold.py
    progress_heuristic.py
    oracle.py
    registry.py
  runner/
    run_benchmark.py
    sweep.py
  evaluation/
    metrics.py
    trajectory.py
    oracle.py
  configs/
    default.yaml
    mock.yaml
    sweep_toy.yaml
  runs/
  reports/
  README.md
```

На первом этапе не обязательно сразу переносить все файлы в пакетную структуру. Достаточно инкрементально ввести недостающие слои: backend abstraction, policy registry, metrics module, run directories и CLI.

### 5.2. Основные компоненты

| Компонент | Ответственность |
|---|---|
| `Dataset` | Хранит задачи, тесты, metadata, oracle labels |
| `Environment` | Запускает решение и тесты, возвращает pass/fail результат |
| `DeveloperAgent` | Генерирует код на выбранном tier: weak/strong/human/mock |
| `ReviewerAgent` | Проверяет код до тестов и дает hint |
| `TesterAgent` | Запускает тесты и формирует test report |
| `ManagerAgent` / `Policy` | Принимает действие на основе состояния |
| `Backend` | Инкапсулирует OpenAI/Gemini/mock вызовы |
| `Runner` | Исполняет эпизоды и сохраняет артефакты |
| `Metrics` | Считает качество, стоимость и ошибки эскалации |
| `Reports` | Собирает таблицы и Markdown summary |

### 5.3. CLI

Минимальный интерфейс:

```bash
python -m runner.run_benchmark \
  --dataset dataset/tasks.json \
  --backend mock \
  --policy retry_then_escalate \
  --config configs/default.yaml \
  --output runs/
```

Для сравнения политик:

```bash
python -m runner.sweep \
  --config configs/sweep_toy.yaml
```

### 5.4. YAML-конфигурация

```yaml
dataset:
  path: dataset/tasks.json
  mode: toy_json

backend:
  name: mock
  seed: 42

policy:
  name: retry_then_escalate
  max_weak_attempts: 2
  max_strong_attempts: 1
  confidence_threshold: 0.30
  zero_progress_limit: 2
  max_total_iterations: 7

costs:
  weak_generate: 1.0
  strong_generate: 3.0
  reviewer_call: 0.5
  test_run: 0.5
  human_call: 10.0

logging:
  save_events: true
  save_trajectories: true
  save_debug_log: true
```

## 6. Формат задач и датасета

### 6.1. Текущий формат

Сейчас задача в `dataset/tasks.json` содержит:

```json
{
  "instance_id": "T001",
  "difficulty": "easy",
  "problem_statement": "...",
  "original_code": "...",
  "tests": [
    {
      "name": "test_sum_basic",
      "description": "...",
      "assertions": [
        {"custom": true, "code": "assert ..."}
      ]
    }
  ]
}
```

Этого достаточно для toy-прототипа, но недостаточно для полноценного benchmark.

### 6.2. Расширенный JSON-формат

```json
{
  "instance_id": "T004",
  "task_type": "bug_fix",
  "difficulty": "medium",
  "tags": ["api", "empty_input", "response_format"],
  "problem_statement": "Fix API response formatting for empty results.",
  "original_code": "def format_response(items): ...",
  "entry_point": "format_response",
  "expected_behavior": "Return {'items': []} for empty input.",
  "tests": [
    {
      "name": "test_empty_response",
      "description": "Empty list should be represented explicitly.",
      "assertions": [
        {"custom": true, "code": "assert format_response([]) == {'items': []}"}
      ]
    }
  ],
  "reference_solution": "def format_response(items): ...",
  "oracle_label": "need_strong",
  "repro_command": "pytest -q"
}
```

### 6.3. File-based формат для следующего этапа

```text
cases/T004/
  issue.md
  solution.py
  test_solution.py
  metadata.yaml
  reference_solution.py
```

`metadata.yaml`:

```yaml
task_id: T004
task_type: bug_fix
difficulty: medium
entry_point: format_response
oracle_min_tier: strong
tags:
  - api
  - response_format
repro_command: pytest -q
```

### 6.4. Требования к задачам

Каждая задача должна удовлетворять условиям:

1. buggy version не проходит хотя бы один целевой тест;
2. reference solution проходит все тесты;
3. тесты детерминированы;
4. задача не зависит от сети и внешних сервисов;
5. задача имеет понятную категорию бага;
6. задача имеет `difficulty` и `oracle_label`;
7. задача воспроизводится одной командой;
8. тесты проверяют не только happy path, но и edge cases.

### 6.5. План расширения toy dataset

Для первого устойчивого прототипа достаточно 10-15 задач. Рекомендуемые типы:

| ID | Тип бага | Пример |
|---|---|---|
| T001 | off-by-one | последний элемент списка не учитывается |
| T002 | ttl_expiration | неверная проверка истечения TTL |
| T003 | rate_limit | неверное скользящее окно |
| T004 | empty_input | пустой список обрабатывается как ошибка |
| T005 | sorting | сортировка по неправильному ключу |
| T006 | filtering | фильтр пропускает невалидные записи |
| T007 | validation | email/phone validation принимает неверные значения |
| T008 | response_format | API возвращает неправильную структуру |
| T009 | date_parsing | неверная обработка timezone/date format |
| T010 | discount_calc | скидка считается до налога вместо после |
| T011 | pagination | неверный offset/limit |
| T012 | idempotency | повторный вызов меняет состояние |
| T013 | permissions | роль пользователя проверяется неполно |
| T014 | retry_logic | повтор запроса не ограничен |
| T015 | cache_key | ключ кэша не учитывает параметр запроса |

## 7. Логирование траекторий

### 7.1. Почему event log недостаточен

Текущий `mas_runner.py` пишет события вида:

- `generate_code`;
- `code_review`;
- `run_tests`;
- `manager_decision`;
- `escalation_event`;
- `final`.

Это полезно для отладки, но для сравнения политик нужен нормализованный формат переходов:

```text
state -> action -> next_state -> reward -> done
```

Такой формат позволяет:

- сравнивать policies на одинаковых задачах;
- считать regret относительно oracle;
- обучать policy на собранных траекториях;
- анализировать ошибки эскалации.

### 7.2. Event log

`events.json` должен хранить подробные события runner:

```json
{
  "event": "run_tests",
  "task_id": "T002",
  "step": 3,
  "from": "tester",
  "to": "manager",
  "pass_rate": 0.67,
  "tests_passed": 2,
  "tests_total": 3,
  "failures": ["test_ttl_expired failed"]
}
```

### 7.3. Trajectory log

`traces.json` должен хранить MDP-переходы:

```json
{
  "episode_id": "run_001_T002",
  "task_id": "T002",
  "step": 2,
  "state": {
    "current_tier": "weak",
    "attempt_weak": 2,
    "attempt_strong": 0,
    "last_pass_rate": 0.33,
    "last_confidence": 0.42,
    "last_review_score": 0.50,
    "cost_so_far": 2.0,
    "tests_run_so_far": 1,
    "no_progress_steps": 1
  },
  "action": "switch_to_strong",
  "next_state": {
    "current_tier": "strong",
    "attempt_weak": 2,
    "attempt_strong": 0,
    "last_pass_rate": 0.33,
    "cost_so_far": 2.0
  },
  "reward": -3.0,
  "done": false
}
```

### 7.4. Список действий

| Action | Значение |
|---|---|
| `generate_weak` | Запустить weak developer |
| `generate_strong` | Запустить strong developer |
| `send_to_review` | Отправить код reviewer |
| `request_changes` | Вернуть developer с hint |
| `run_tests` | Запустить тесты |
| `switch_to_strong` | Эскалировать на сильную модель |
| `call_human` | Передать задачу человеку |
| `accept` | Принять решение |
| `stop` | Остановиться |

### 7.5. Reward

Для первого прототипа можно использовать простую reward function:

```text
reward = success_bonus
         + pass_rate_delta
         - action_cost
         - no_progress_penalty
         - unnecessary_escalation_penalty
```

Пример:

| Событие | Reward |
|---|---|
| Все тесты прошли | `+10` |
| Pass rate вырос | `+delta_pass_rate * 2` |
| Weak generation | `-1` |
| Strong generation | `-3` |
| Test run | `-0.5` |
| Human escalation | `-10` |
| Повтор без прогресса | `-1` |
| Ранняя ненужная эскалация | `-2` |

## 8. Метрики и baseline policies

### 8.1. Метрики качества решения

| Метрика | Формула / смысл |
|---|---|
| `solved_rate` | доля задач, где итог `success` |
| `final_pass_rate` | средний pass rate в конце эпизода |
| `initial_failures` | сколько тестов падало на исходном коде |
| `pass_rate_delta` | `final_pass_rate - initial_pass_rate` |
| `num_iterations` | число генераций developer |
| `num_test_runs` | число запусков тестов |
| `num_reviews` | число ревью |

### 8.2. Метрики стоимости и эскалации

| Метрика | Формула / смысл |
|---|---|
| `cost_to_green` | стоимость до первого успешного прохождения тестов |
| `total_cost` | полная стоимость эпизода |
| `strong_escalation_rate` | доля задач с переходом на strong |
| `human_escalation_rate` | доля задач с обращением к человеку |
| `empty_iterations` | число попыток без прироста pass rate |
| `budget_exceeded_rate` | доля задач, остановленных по бюджету |

### 8.3. Метрики ошибок политики

| Метрика | Что показывает |
|---|---|
| `premature_escalation` | политика перешла на strong/human, хотя oracle показывает, что weak могла решить |
| `missed_escalation` | политика слишком долго не эскалировала задачу, которую weak не решает |
| `unnecessary_human_call` | человек вызван там, где strong достаточно |
| `policy_regret` | разница стоимости/качества между policy и oracle policy |

### 8.4. Oracle labels

Для toy benchmark можно использовать следующие метки:

| Oracle label | Значение |
|---|---|
| `weak_enough` | weak model решает задачу |
| `need_strong` | weak не решает, strong решает |
| `need_human` | weak и strong не решают, нужен человек |
| `unsolved` | задача не решается текущими средствами |

### 8.5. Baseline policies

| Policy | Правило | Зачем нужна |
|---|---|---|
| `fixed_weak` | всегда использовать weak | нижняя граница стоимости |
| `fixed_strong` | всегда использовать strong | верхняя граница качества при высокой цене |
| `retry_then_escalate` | `weak x N -> strong x M -> human` | основной простой baseline |
| `confidence_threshold` | эскалировать при `confidence < threshold` | использует сигнал модели |
| `progress_heuristic` | эскалировать при отсутствии прироста pass rate | использует объективный test signal |
| `reviewer_driven` | эскалировать по рекомендации reviewer | проверяет пользу reviewer |
| `random_policy` | случайный выбор действия с seed | нижняя случайная граница |
| `oracle_policy` | выбирать минимальный достаточный tier | верхняя недостижимая граница |

## 9. Экспериментальный дизайн

### 9.1. Минимальный эксперимент

1. Зафиксировать toy dataset из 10-15 задач.
2. Для каждой задачи проверить, что исходный код падает хотя бы на одном тесте.
3. Запустить все baseline policies на одинаковом dataset.
4. Для каждого запуска сохранить:
   - `config.json`;
   - `events.json`;
   - `traces.json`;
   - `metrics.json`;
   - `summary.md`.
5. Сравнить политики по solved rate, cost, test runs, escalation rate и policy regret.

### 9.2. Таблица результатов

Пример ожидаемой таблицы:

| Policy | Solved | Avg cost | Avg iterations | Strong rate | Human rate | Avg final pass rate |
|---|---:|---:|---:|---:|---:|---:|
| fixed_weak | 40% | 1.0 | 1.0 | 0% | 0% | 0.58 |
| fixed_strong | 75% | 3.0 | 1.0 | 100% | 0% | 0.82 |
| retry_then_escalate | 80% | 4.7 | 2.4 | 55% | 10% | 0.86 |
| confidence_threshold | 78% | 4.1 | 2.1 | 48% | 12% | 0.84 |
| progress_heuristic | 82% | 4.4 | 2.2 | 50% | 8% | 0.88 |
| oracle_policy | 90% | 3.6 | 1.4 | 42% | 6% | 0.93 |

Числа в этой таблице примерные. В финальной работе их нужно заменить результатами реального запуска.

### 9.3. Какие выводы можно делать

По результатам экспериментов можно анализировать:

- насколько weak model экономит стоимость;
- насколько strong model повышает solved rate;
- помогает ли reviewer до тестов;
- когда confidence полезен, а когда шумит;
- сколько стоит преждевременная эскалация;
- сколько задач доходят до человека;
- какие категории задач чаще требуют strong/human.

## 10. Технологический отчет

Этот раздел можно использовать как основу отдельного технического отчета или технологической статьи. Он описывает не только идею, но и инженерную реализацию benchmark prototype.

### 10.1. Назначение системы

Benchmark-escalation - это среда для воспроизводимого запуска мультиагентного процесса решения задач программирования. Система принимает набор задач, выбранную policy и backend моделей, после чего исполняет эпизоды и сохраняет артефакты для анализа.

Главный объект оценки - не отдельная LLM, а политика управления процессом. Поэтому система должна уметь запускать одинаковые задачи при разных стратегиях:

- дешево решать все weak model;
- сразу использовать strong model;
- повторять weak несколько раз;
- эскалировать по confidence;
- эскалировать по результатам тестов;
- обращаться к человеку после исчерпания бюджета.

### 10.2. Текущая реализация

Текущий прототип уже реализует минимальный multi-agent loop:

```text
Developer -> Manager -> Reviewer -> Manager -> Tester -> Manager
```

Роли:

- `DeveloperAgent` генерирует код;
- `ReviewerAgent` оценивает качество и дает hint;
- `TesterAgent` запускает тесты;
- `ManagerAgent` принимает решения об эскалации;
- `Environment` исполняет тесты;
- `mas_runner.py` связывает все компоненты.

Текущий поток:

1. Manager выбирает текущий tier: weak или strong.
2. Developer генерирует код и confidence.
3. Manager решает, отправлять ли код на review.
4. Reviewer возвращает `approve`, `request_changes` или `escalate`.
5. Manager решает, запускать ли тесты.
6. Tester запускает тесты и возвращает pass rate.
7. Manager принимает итоговое действие: accept, retry, escalate strong, escalate human или stop.

### 10.3. Целевая доработка кода

#### 10.3.1. Backend layer

Проблема: сейчас `llm_client.py` напрямую зависит от OpenAI API. Для benchmark это неудобно: результаты дорогие, не всегда воспроизводимые, требуют ключей.

Решение: ввести backend abstraction.

```python
class Backend:
    def generate_code(self, task, tier, reviewer_hint=""):
        raise NotImplementedError

    def review_code(self, task, code):
        raise NotImplementedError
```

Реализации:

- `MockBackend` - детерминированные ответы для экспериментов;
- `OpenAIBackend` - реальные OpenAI-модели;
- `GeminiBackend` - реальные Gemini-модели;
- `HumanBackend` - заглушка/ручной ввод для human escalation.

Mock сценарии:

```yaml
mock_scenarios:
  T001:
    weak: solve
    strong: solve
  T002:
    weak: fail_once_then_solve
    strong: solve
  T003:
    weak: fail
    strong: partial
    human: solve
```

#### 10.3.2. Policy layer

Проблема: параметры политики сейчас создаются прямо в `mas_runner.py`:

```python
policy = ManagerPolicy(
    max_weak_attempts=2,
    max_strong_attempts=1,
    confidence_threshold=0.3,
    max_total_iterations=7,
)
```

Решение: вынести политики в отдельный модуль и выбирать их через config/CLI.

```python
policy = policy_registry.create(config["policy"])
```

Это позволит запускать одинаковый dataset разными политиками без изменения кода.

#### 10.3.3. Metrics layer

Проблема: метрики сейчас считаются внутри runner. Это связывает запуск и анализ.

Решение:

```text
evaluation/
  metrics.py
  trajectory.py
  oracle.py
```

`metrics.py` должен принимать `events` и `trajectories`, а возвращать словарь:

```json
{
  "solved_rate": 0.8,
  "avg_cost": 4.7,
  "avg_iterations": 2.4,
  "strong_escalation_rate": 0.55,
  "human_escalation_rate": 0.10,
  "avg_final_pass_rate": 0.86
}
```

#### 10.3.4. Run directories

Проблема: один файл `mas_traces.json` в корне легко перезаписать, а сравнивать прогоны неудобно.

Решение: каждый запуск получает отдельную директорию.

```text
runs/run_001/
  config.json
  events.json
  traces.json
  metrics.json
  summary.md
```

`summary.md` должен содержать:

- дату и config запуска;
- список задач;
- выбранную policy;
- backend;
- таблицу метрик;
- ошибки и warning;
- ссылку на полные traces.

#### 10.3.5. Environment isolation

Проблема: текущие тесты выполняются через `exec(solution_code, ns)`. Для toy-задач это допустимый быстрый прототип, но для benchmark это риск.

Решение по этапам:

1. Stage 1: оставить `exec`, но использовать только локальные toy-задачи без внешнего ввода.
2. Stage 2: перейти к file-based cases и запускать `pytest` в subprocess.
3. Stage 3: для real repositories использовать Docker/harness по аналогии со SWE-bench.

### 10.4. Пример реализации runner

Псевдокод целевого runner:

```python
def run_benchmark(config):
    tasks = load_dataset(config.dataset)
    backend = create_backend(config.backend)
    policy = create_policy(config.policy)
    metrics_accumulator = []

    run_dir = create_run_dir(config)

    for task in tasks:
        episode = run_episode(
            task=task,
            backend=backend,
            policy=policy,
            costs=config.costs,
        )
        save_events(run_dir, episode.events)
        save_trajectories(run_dir, episode.trajectories)
        metrics_accumulator.append(compute_task_metrics(episode))

    metrics = aggregate_metrics(metrics_accumulator)
    save_metrics(run_dir, metrics)
    build_summary(run_dir, metrics)
```

### 10.5. Пример state builder

```python
def build_state(context):
    return {
        "task_id": context.task_id,
        "difficulty": context.difficulty,
        "current_tier": context.current_tier,
        "weak_attempts": context.weak_attempts,
        "strong_attempts": context.strong_attempts,
        "last_pass_rate": context.last_pass_rate,
        "last_confidence": context.last_confidence,
        "last_review_score": context.last_review_score,
        "tests_run_so_far": context.tests_run_so_far,
        "cost_so_far": context.cost_so_far,
        "no_progress_steps": context.no_progress_steps,
    }
```

### 10.6. Пример summary.md

```markdown
# Run summary: run_001

Backend: mock
Policy: retry_then_escalate
Dataset: toy_v1
Seed: 42

| Metric | Value |
|---|---:|
| solved_rate | 0.80 |
| avg_cost | 4.70 |
| avg_iterations | 2.40 |
| strong_escalation_rate | 0.55 |
| human_escalation_rate | 0.10 |
| avg_final_pass_rate | 0.86 |

## Failed tasks

| Task | Difficulty | Final pass rate | Reason |
|---|---|---:|---|
| T003 | hard | 0.50 | strong did not fix sliding window |
```

### 10.7. Что писать в технологической статье

Если технологический отчет нужно оформить в стиле статьи, структура может быть такой:

1. **Проблема.** LLM-агенты умеют писать код, но непонятно, когда нужно эскалировать задачу.
2. **Почему существующих benchmark недостаточно.** HumanEval/SWE-bench оценивают финал, но не управленческую траекторию.
3. **Идея.** Представить решение задачи как episode с действиями manager.
4. **Архитектура.** Dataset, Environment, Agents, Policies, Runner, Metrics.
5. **Формат данных.** JSON задач, event log, trajectory log.
6. **Политики.** FixedWeak, FixedStrong, RetryThenEscalate, ConfidenceThreshold, ProgressHeuristic, Oracle.
7. **Метрики.** Solved, cost, pass rate, escalation rates, regret.
8. **Эксперименты.** Сравнение baseline policies на toy dataset.
9. **Ограничения.** Toy-задачи, mock backend, exec-тесты.
10. **Дальнейшее развитие.** Pytest subprocess, SWE-bench-like cases, real repositories.

Пример вводного абзаца для статьи:

> В большинстве benchmark для LLM-программирования результатом считается финальный патч: тесты прошли или нет. Но в реальной агентной разработке важно не только получить патч, но и управлять процессом: решать, когда повторить попытку, когда запускать тесты, когда переходить к более сильной модели и когда передавать задачу человеку. В этой работе я описываю прототип benchmark-escalation - среды, которая сохраняет траектории решений и позволяет сравнивать политики эскалации по качеству, стоимости и числу обращений к дорогим ресурсам.

Пример абзаца про архитектуру:

> Система разделена на несколько слоев. Dataset хранит задачи и тесты, Environment отвечает за запуск решения, Developer генерирует код, Reviewer выполняет предварительную проверку, Tester запускает тесты, а Manager выбирает следующее действие. Отдельный слой Policies позволяет заменить стратегию эскалации без изменения runner. Каждый прогон сохраняется в директорию `runs/run_XXX`, где лежат конфигурация, события, MDP-траектории, метрики и краткий summary.

Пример абзаца про результат:

> Минимальный результат прототипа - возможность одной командой запустить несколько политик на одном наборе задач и получить таблицу сравнения. Такая таблица показывает не только долю решенных задач, но и цену решения: сколько раз запускалась сильная модель, сколько было тестовых прогонов, сколько задач дошло до человека и где политика ошиблась с моментом эскалации.

## 11. Инкрементальный план реализации

План лучше описывать не календарными сроками, а проверяемыми инженерными этапами.

| Этап | Цель | Основные изменения | Проверка готовности |
|---|---|---|---|
| Stage 0 | Починить текущий запуск | исправить `compute_oracle.py`, синхронизировать названия провайдеров | `python mas_runner.py`; `python compute_oracle.py` |
| Stage 1 | Сделать воспроизводимый toy benchmark | добавить mock backend, config, run directories | запуск без API-ключа |
| Stage 2 | Вынести политики | `policies/`, registry, CLI `--policy` | запуск 5 baseline policies |
| Stage 3 | Нормализовать логи | `events.json`, `traces.json`, reward function | есть `state/action/next_state/reward` |
| Stage 4 | Вынести метрики | `evaluation/metrics.py`, `summary.md` | автоматическая таблица метрик |
| Stage 5 | Расширить dataset | 10-15 toy-задач, oracle labels | все задачи имеют reference solution |
| Stage 6 | Провести эксперименты | sweep по policies | `reports/baselines.md` |
| Stage 7 | Подготовить документацию | README, add-task guide, add-policy guide, technical report | новый человек может воспроизвести запуск |

## 12. Критерии готовности семестрового результата

Benchmark prototype можно считать готовым, если выполнены условия:

1. Есть 10-15 задач в toy dataset.
2. Каждая задача имеет failing buggy version и passing reference solution.
3. Есть mock backend, позволяющий запускать benchmark без API-ключей.
4. Есть минимум 5 baseline policies.
5. Есть единая команда запуска benchmark.
6. Каждый запуск сохраняет `config.json`, `events.json`, `traces.json`, `metrics.json`, `summary.md`.
7. Траектории содержат `state`, `action`, `next_state`, `reward`, `done`.
8. Метрики считаются автоматически.
9. Есть таблица сравнения baseline policies.
10. README описывает quickstart, формат задачи и добавление новой policy.
11. Технический отчет описывает архитектуру, ограничения и результаты экспериментов.

## 13. Риски и способы снижения

| Риск | Последствие | Снижение |
|---|---|---|
| Зависимость от внешних LLM API | эксперименты дорогие и невоспроизводимые | mock backend как основной режим разработки |
| Слишком ранний переход к SWE-bench/Docker | прототип становится тяжелым | сначала toy JSON, затем pytest cases, потом real repos |
| `exec` остается в production-like runner | риск безопасности и нестабильности | заменить на subprocess/pytest для file-based cases |
| Нет oracle labels | нельзя считать regret и ошибки эскалации | реализовать oracle computation после стабилизации backend |
| Политики зашиты в runner | нельзя честно сравнивать strategies | policy registry и YAML config |
| Логи остаются только event-based | нельзя обучать policy | отдельный trajectory builder |
| Dataset слишком простой | политики отличаются слабо | добавить задачи разных типов и сложности |

## 14. Ожидаемые результаты

По итогам семестровой работы должен получиться следующий набор артефактов:

1. Код benchmark prototype.
2. Toy dataset на 10-15 задач.
3. Mock backend.
4. Backend interface для будущих OpenAI/Gemini запусков.
5. Набор baseline policies.
6. Runner с CLI.
7. Run artifact format.
8. Trajectory logging.
9. Metrics module.
10. Таблица baseline experiments.
11. README.
12. Технологический отчет.
13. Рекомендации по развитию до real-repository benchmark.

## 15. Заключение

Существующие benchmark для LLM-программирования хорошо измеряют качество финального решения, но почти не измеряют качество управления процессом решения. Для исследования политик эскалации нужен benchmark другого типа: он должен хранить последовательность состояний, действий, результатов тестов, стоимости и итоговых наград.

Текущий прототип benchmark-escalation уже содержит важную основу: роли агентов, manager policy, environment, toy dataset и первичные метрики. Основная инженерная работа состоит в стабилизации этого прототипа: убрать жесткую зависимость от API, добавить mock backend, вынести политики и метрики, расширить dataset, нормализовать trajectory logging и сделать воспроизводимые run artifacts.

Такой benchmark позволит сравнивать не только модели, но и стратегии их использования. Это соответствует исходной исследовательской идее: определить, когда агент должен продолжать самостоятельное решение, когда переходить к более сильной модели, когда использовать инструменты и когда привлекать человека.

## 16. Источники и ориентиры

1. SWE-bench: https://www.swebench.com/
2. SWE-bench GitHub: https://github.com/SWE-bench/SWE-bench
3. HumanEval: https://github.com/openai/human-eval
4. EvalPlus: https://github.com/evalplus/evalplus
5. BugsInPy: https://github.com/soarsmu/BugsInPy
6. Defects4J: https://github.com/rjust/defects4j
7. Пример технической статьи на Хабре: https://habr.com/ru/articles/957694/
8. Пример технического отчета/статьи ИТМО на Хабре: https://habr.com/ru/companies/spbifmo/articles/725800/
9. Пример технического отчета/статьи ИТМО на Хабре: https://habr.com/ru/companies/spbifmo/articles/838598/
10. Пример технического отчета/статьи ИТМО на Хабре: https://habr.com/ru/companies/spbifmo/articles/906018/
