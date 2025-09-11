## 📘 EvaluationManager and Evaluation Documentation

The `EvaluationManager` and `Evaluation` classes are responsible for assessing the quality, compliance, and accuracy of generated responses. These evaluations are applied directly by the **orchestrator** after the message has been generated. The orchestrator calls the `EvaluationManager` to run the evaluations on the generated message, ensuring that the response meets the required standards before being finalized.

---

### 🔑 Evaluation Overview

The `Evaluation` class is an abstract base class that defines the structure and behavior of individual evaluations. Each evaluation must implement the following methods:

1. **`get_name`**: Returns the unique name of the evaluation.
2. **`get_assessment_type`**: Specifies the type of assessment (e.g., hallucination or compliance).
3. **`run`**: Executes the evaluation logic on the response.
4. **`evaluation_metric_to_assessment`**: Converts the evaluation result into a user-facing assessment message.

#### Evaluation Class Definition:
```python
class Evaluation(ABC):
    def __init__(self, name: EvaluationMetricName):
        self.name = name

    def get_name(self) -> EvaluationMetricName:
        """Returns the unique name of the evaluation."""
        return self.name

    def get_assessment_type(self) -> ChatMessageAssessmentType:
        """Specifies the type of assessment (e.g., hallucination or compliance)."""
        raise NotImplementedError(
            "Subclasses must implement this method to return the assessment type."
        )

    async def run(
        self, loop_response: LanguageModelStreamResponse
    ) -> EvaluationMetricResult:
        """Executes the evaluation logic."""
        raise NotImplementedError("Subclasses must implement this method.")

    async def evaluation_metric_to_assessment(
        self, evaluation_result: EvaluationMetricResult
    ) -> EvaluationAssessmentMessage:
        """Converts the evaluation result into a user-facing assessment message."""
        raise NotImplementedError(
            "Subclasses must implement this method to convert evaluation results to assessment messages."
        )
```

---

### 🔑 EvaluationManager Overview

The `EvaluationManager` is responsible for managing and executing evaluations. It allows evaluations to be registered, executed asynchronously, and their results integrated into the chat interface. The manager ensures that evaluations are run efficiently and their outcomes are displayed to the user.

---

### 🛠️ Key Functionalities of EvaluationManager

registers and collects evaluations like the hallucination checker.

#### 1. **Evaluation Management**
   - **`add_evaluation(evaluation: Evaluation)`**  
     Registers an evaluation instance with the manager.  
     ```python
     def add_evaluation(self, evaluation: Evaluation):
         self._evaluations[evaluation.get_name()] = evaluation
     ```

   - **`get_evaluation_by_name(name: EvaluationMetricName) -> Evaluation | None`**  
     Retrieves an evaluation instance by its name.  
     ```python
     def get_evaluation_by_name(self, name: EvaluationMetricName) -> Evaluation | None:
         return self._evaluations.get(name)
     ```

#### 2. **Evaluation Execution**
   - **`run_evaluations(selected_evaluation_names: list[EvaluationMetricName], loop_response: LanguageModelStreamResponse, assistant_message_id: str)`**  
     Executes the selected evaluations asynchronously. Results are processed and returned as a list of `EvaluationMetricResult`.  
     ```python
     async def run_evaluations(
         self,
         selected_evaluation_names: list[EvaluationMetricName],
         loop_response: LanguageModelStreamResponse,
         assistant_message_id: str,
     ) -> list[EvaluationMetricResult]:
         tasks = [
             task_executor.execute_async(
                 self.execute_evaluation_call,
                 loop_response=loop_response,
                 evaluation_name=evaluation_name,
                 assistant_message_id=assistant_message_id,
             )
             for evaluation_name in selected_evaluation_names
         ]
         evaluation_results = await asyncio.gather(*tasks)
         return evaluation_results_unpacked
     ```

   - **`execute_evaluation_call(evaluation_name: EvaluationMetricName, loop_response: LanguageModelStreamResponse, assistant_message_id: str)`**  
     Executes a single evaluation and returns its result.  
     ```python
     async def execute_evaluation_call(
         self,
         evaluation_name: EvaluationMetricName,
         loop_response: LanguageModelStreamResponse,
         assistant_message_id: str,
     ) -> EvaluationMetricResult:
         evaluation_instance = self.get_evaluation_by_name(evaluation_name)
         if evaluation_instance:
             await self._create_assistant_message(evaluation_instance, assistant_message_id)
             evaluation_metric_result = await evaluation_instance.run(loop_response)
             await self._show_message_assessment(
                 evaluation_instance, evaluation_metric_result, assistant_message_id
             )
             return evaluation_metric_result
         return EvaluationMetricResult(
             name=evaluation_name,
             is_positive=True,
             value="RED",
             reason=f"Evaluation named {evaluation_name} not found",
             error=Exception("Evaluation named {evaluation_name} not found"),
         )
     ```

#### 3. **Result Processing**
   - **`_create_evaluation_metric_result(result: Result[EvaluationMetricResult], evaluation_name: EvaluationMetricName)`**  
     Processes the result of an evaluation and ensures it is valid.  
     ```python
     def _create_evaluation_metric_result(
         self,
         result: Result[EvaluationMetricResult],
         evaluation_name: EvaluationMetricName,
     ) -> EvaluationMetricResult:
         if not result.success:
             return EvaluationMetricResult(
                 name=evaluation_name,
                 is_positive=True,
                 value="RED",
                 reason=str(result.exception),
                 error=Exception("Evaluation result is not successful"),
             )
         return result.unpack()
     ```

#### 4. **Chat Integration**
   - **`_show_message_assessment(evaluation_instance: Evaluation, evaluation_metric_result: EvaluationMetricResult, assistant_message_id: str)`**  
     Updates the chat interface with the evaluation results.  
     ```python
     async def _show_message_assessment(
         self,
         evaluation_instance: Evaluation,
         evaluation_metric_result: EvaluationMetricResult,
         assistant_message_id: str,
     ) -> None:
         evaluation_assessment_message = (
             await evaluation_instance.evaluation_metric_to_assessment(
                 evaluation_metric_result
             )
         )
         await self._chat_service.modify_message_assessment_async(
             assistant_message_id=assistant_message_id,
             status=evaluation_assessment_message.status,
             title=evaluation_assessment_message.title,
             explanation=evaluation_assessment_message.explanation,
             label=evaluation_assessment_message.label,
             type=evaluation_assessment_message.type,
         )
     ```

   - **`_create_assistant_message(evaluation_instance: Evaluation, assistant_message_id: str)`**  
     Creates a placeholder message in the chat interface while the evaluation is pending.  
     ```python
     async def _create_assistant_message(
         self, evaluation_instance: Evaluation, assistant_message_id: str
     ):
         await self._chat_service.create_message_assessment_async(
             assistant_message_id=assistant_message_id,
             status=ChatMessageAssessmentStatus.PENDING,
             type=evaluation_instance.get_assessment_type(),
         )
     ```
