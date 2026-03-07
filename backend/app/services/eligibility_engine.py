from typing import Dict, Any, List, Optional
import logging

from app.models.service import EligibilityCriterion, ServiceGuide

logger = logging.getLogger(__name__)


class Question(dict):
    """Eligibility question"""
    def __init__(self, question_id: str, text: str, question_type: str, required: bool = True):
        super().__init__(
            question_id=question_id,
            text=text,
            question_type=question_type,
            required=required
        )


class FailedCriterion(dict):
    """Failed eligibility criterion"""
    def __init__(self, criterion_id: str, description: str, reason: str):
        super().__init__(
            criterion_id=criterion_id,
            description=description,
            reason=reason,
            possible_remedies=[]
        )


class EligibilityResult(dict):
    """Eligibility evaluation result"""
    def __init__(self, eligible: bool, met_criteria: List[str], failed_criteria: List[FailedCriterion]):
        super().__init__(
            eligible=eligible,
            met_criteria=met_criteria,
            failed_criteria=failed_criteria,
            confidence=1.0,
            appeal_available=len(failed_criteria) > 0
        )


class AlternativeService(dict):
    """Alternative service suggestion"""
    def __init__(self, service_id: str, service_name: str, reason: str):
        super().__init__(
            service_id=service_id,
            service_name=service_name,
            reason=reason
        )


class EligibilityEngine:
    """Engine for evaluating service eligibility"""
    
    def evaluate_eligibility(
        self,
        service_id: str,
        criteria: List[EligibilityCriterion],
        responses: Dict[str, Any]
    ) -> EligibilityResult:
        """Evaluate eligibility based on criteria and user responses"""
        met_criteria = []
        failed_criteria = []
        
        for criterion in criteria:
            if not criterion.required:
                continue
            
            # Simple validation logic
            criterion_met = self._validate_criterion(criterion, responses)
            
            if criterion_met:
                met_criteria.append(criterion.criterion_id)
            else:
                failed_criteria.append(
                    FailedCriterion(
                        criterion_id=criterion.criterion_id,
                        description=criterion.description,
                        reason=criterion.failure_message
                    )
                )
        
        eligible = len(failed_criteria) == 0
        return EligibilityResult(eligible, met_criteria, failed_criteria)
    
    def _validate_criterion(
        self,
        criterion: EligibilityCriterion,
        responses: Dict[str, Any]
    ) -> bool:
        """Validate a single criterion"""
        # Simplified validation - in production would be more sophisticated
        response_value = responses.get(criterion.criterion_id)
        
        if response_value is None:
            return False
        
        rule_type = criterion.validation_rule.rule_type
        
        if rule_type == "exists":
            return bool(response_value)
        elif rule_type == "equals":
            expected = criterion.validation_rule.parameters.get("value")
            return response_value == expected
        elif rule_type == "category_check":
            return bool(response_value)
        
        return True
    
    def generate_questions(
        self,
        criteria: List[EligibilityCriterion],
        existing_responses: Dict[str, Any]
    ) -> List[Question]:
        """Generate clarifying questions for missing criteria"""
        questions = []
        
        for criterion in criteria:
            if criterion.criterion_id not in existing_responses:
                questions.append(
                    Question(
                        question_id=criterion.criterion_id,
                        text=criterion.description,
                        question_type="yes_no",
                        required=criterion.required
                    )
                )
        
        return questions
    
    def suggest_alternatives(
        self,
        service_id: str,
        failed_criteria: List[str],
        all_services: List[ServiceGuide]
    ) -> List[AlternativeService]:
        """Suggest alternative services when ineligible"""
        alternatives = []
        
        # Find services with fewer or different requirements
        for service in all_services:
            if service.service_id == service_id:
                continue
            
            # Check if this service might be suitable
            required_criteria = [c for c in service.eligibility_criteria if c.required]
            if len(required_criteria) < len(failed_criteria):
                alternatives.append(
                    AlternativeService(
                        service_id=service.service_id,
                        service_name=service.service_name,
                        reason="Has fewer eligibility requirements"
                    )
                )
        
        return alternatives[:3]  # Return top 3 alternatives


eligibility_engine = EligibilityEngine()
