"""
Consultant knowledge base for Task Manager.
Contains best practices and guidelines for consultants.
"""
from typing import Dict, List, Any, Optional
from core.knowledge.knowledge_base import KnowledgeBase

class ConsultantKnowledge(KnowledgeBase):
    """Knowledge base for consultant guidelines and best practices."""
    
    def __init__(self, source_type: str = "embedded", source_location: Optional[str] = None):
        """
        Initialize the consultant knowledge base.
        
        Args:
            source_type: Type of source ('file', 'embedded').
            source_location: Location of the source file (if source_type is 'file').
        """
        super().__init__(
            name="Consultant Guidelines",
            source_type=source_type,
            source_location=source_location
        )
    
    def _load_embedded(self) -> bool:
        """
        Load embedded consultant guidelines.
        
        Returns:
            bool: True if loading was successful.
        """
        # Basic embedded consultant guidelines
        self.content = """# Consultant Best Practices and Guidelines

## Communication Standards

### Client Communication
All client communications should be professional, timely, and value-focused. Respond to client inquiries within 4 business hours. Document all client interactions in the project management system.

### Internal Communication
Team communications should be transparent and proactive. Use appropriate channels for different types of communication. Update project status daily in the task management system.

### Status Reporting
Provide weekly status reports that include:
- Accomplishments
- Upcoming tasks
- Issues/risks
- Decisions needed
- Budget status

## Task Management

### Task Documentation
All tasks must include:
- Clear description of the work
- Context and purpose
- Expected outcome
- Estimated effort
- Priority level

### Task Tracking
Update task status daily. Use the appropriate status values:
- Completed: work is 100% finished
- In Progress: work has started but isn't complete
- Pending: work hasn't started
- Blocked: work cannot progress due to dependencies

### Time Tracking
Record time spent on tasks accurately and daily. Categorize time by project, phase, and activity type.

## Deliverable Standards

### Document Quality
All deliverables must:
- Follow the approved templates
- Include version control
- Be proofread for spelling and grammar
- Include executive summary for documents over 5 pages
- Be reviewed by a peer before client delivery

### Analysis Deliverables
All analysis must:
- Clearly state methodology
- Cite data sources
- Include data quality assessment
- Provide actionable recommendations
- Consider implementation constraints

## Client Engagement

### Value Delivery
Focus on delivering concrete value in every client interaction. Identify opportunities to exceed expectations. Document value delivered.

### Relationship Building
Build relationships at multiple levels within the client organization. Learn about client's personal and professional goals. Demonstrate understanding of client's industry.

### Issue Management
Address issues proactively. Document all issues including:
- Description
- Impact
- Resolution options
- Recommendation
- Action plan

## Professional Development

### Skill Growth
Continuously develop consulting skills:
- Technical expertise
- Industry knowledge
- Client relationship management
- Problem-solving
- Communication skills

### Knowledge Sharing
Document lessons learned after each project phase. Contribute to the knowledge repository. Mentor junior team members.

## Project Management

### Scope Management
Clearly define project scope in writing. Document and get approval for all scope changes. Assess impact of scope changes on schedule and budget.

### Risk Management
Identify and document risks at project start. Review and update risks weekly. Develop mitigation plans for high-impact risks.

### Quality Assurance
Establish quality criteria at project start. Implement peer reviews for all deliverables. Conduct client satisfaction check-ins.
"""
        
        # Parse the content into sections
        self._parse_sections()
        return True
    
    def get_guidelines_for_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get guidelines for a specific category.
        
        Args:
            category: The category to get guidelines for.
            
        Returns:
            List[Dict[str, Any]]: List of guidelines.
        """
        relevant_sections = []
        category_lower = category.lower()
        
        for section in self.sections:
            if category_lower in section["title"].lower():
                relevant_sections.append(section)
        
        return relevant_sections
    
    def get_task_guidelines(self) -> Dict[str, Any]:
        """
        Get guidelines specifically for task management.
        
        Returns:
            Dict[str, Any]: Task management guidelines.
        """
        task_section = self.get_section("Task Management")
        if task_section:
            # Parse subsections
            documentation = self.get_section("Task Documentation")
            tracking = self.get_section("Task Tracking")
            
            return {
                "overview": task_section,
                "documentation": documentation,
                "tracking": tracking
            }
        
        return {}
    
    def extract_guideline_rules(self) -> List[Dict[str, Any]]:
        """
        Extract specific rules from the guidelines.
        
        Returns:
            List[Dict[str, Any]]: List of rule dictionaries.
        """
        rules = []
        
        # Look for sections with specific requirements
        for section in self.sections:
            content = section["content"]
            
            # Look for lists that start with "must" or similar
            if "must" in content.lower() or "should" in content.lower():
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('-') or line.startswith('*'):
                        # Extract the rule
                        rule_text = line[1:].strip()
                        
                        if "must" in rule_text.lower() or "should" in rule_text.lower():
                            rules.append({
                                "category": section["title"],
                                "rule": rule_text,
                                "importance": "high" if "must" in rule_text.lower() else "medium"
                            })
        
        return rules