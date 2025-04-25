"""
AI-powered analyzers for Task Manager.
Provides insights and analysis of tasks and related data.
"""
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from datetime import datetime

# Import OpenAI client for AI-powered analysis
# We'll use the new OpenAI client structure
from openai import OpenAI

# Import from config for now - will be updated with plugin config later
from config import (
    OPENAI_API_KEY,
    CHAT_MODEL
)

class AnalyzerBase:
    """Base class for analyzers."""
    
    def __init__(self, openai_api_key=None, model=None):
        """
        Initialize the analyzer.
        
        Args:
            openai_api_key: OpenAI API key.
            model: OpenAI model to use.
        """
        self.api_key = openai_api_key or OPENAI_API_KEY
        self.model = model or CHAT_MODEL
        self.client = OpenAI(api_key=self.api_key)
    
    def analyze(self, content, **kwargs):
        """
        Analyze content.
        
        Args:
            content: Content to analyze.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Analysis results.
        """
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement analyze()")

class TaskAnalyzer(AnalyzerBase):
    """Analyzer for tasks."""
    
    def analyze(self, 
                tasks: Union[List[Dict[str, Any]], pd.DataFrame], 
                analysis_type: str = "basic",
                **kwargs) -> Dict[str, Any]:
        """
        Analyze tasks.
        
        Args:
            tasks: Tasks to analyze (list of dictionaries or DataFrame).
            analysis_type: Type of analysis to perform.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Analysis results.
        """
        # Convert list to DataFrame if necessary
        if isinstance(tasks, list):
            tasks_df = pd.DataFrame(tasks)
        else:
            tasks_df = tasks.copy()
            
        # Basic statistics
        if analysis_type == "basic":
            # Handle empty dataframe
            if tasks_df.empty:
                return {
                    "count": 0,
                    "message": "No tasks available for analysis"
                }
                
            # Calculate basic statistics
            result = {
                "count": len(tasks_df),
                "status_distribution": {}
            }
            
            # Status distribution
            if "status" in tasks_df.columns:
                status_counts = tasks_df["status"].value_counts().to_dict()
                result["status_distribution"] = status_counts
                
                # Calculate completion rate
                completed = status_counts.get("Completed", 0)
                result["completion_rate"] = completed / len(tasks_df) if len(tasks_df) > 0 else 0
            
            # Category distribution
            if "category" in tasks_df.columns:
                result["category_distribution"] = tasks_df["category"].value_counts().to_dict()
            
            # Employee distribution
            if "employee" in tasks_df.columns:
                result["employee_distribution"] = tasks_df["employee"].value_counts().to_dict()
            
            # Date statistics
            if "date" in tasks_df.columns:
                # Ensure date is datetime
                if tasks_df["date"].dtype == 'object':
                    tasks_df["date"] = pd.to_datetime(tasks_df["date"], errors='coerce')
                
                valid_dates = tasks_df["date"].dropna()
                if not valid_dates.empty:
                    result["date_range"] = {
                        "min": valid_dates.min().strftime("%Y-%m-%d"),
                        "max": valid_dates.max().strftime("%Y-%m-%d")
                    }
                    
                    # Calculate days since for each task
                    today = pd.Timestamp(datetime.now().date())
                    tasks_df["days_since"] = (today - tasks_df["date"]).dt.days
                    
                    result["age_statistics"] = {
                        "average_age": tasks_df["days_since"].mean(),
                        "max_age": tasks_df["days_since"].max(),
                        "tasks_older_than_7_days": int(sum(tasks_df["days_since"] > 7))
                    }
            
            return result
            
        # Productivity analysis
        elif analysis_type == "productivity":
            # Handle empty dataframe
            if tasks_df.empty:
                return {
                    "productivity_score": 0,
                    "message": "No tasks available for productivity analysis"
                }
                
            # Calculate task completion over time
            if "date" in tasks_df.columns and "status" in tasks_df.columns:
                # Ensure date is datetime
                if tasks_df["date"].dtype == 'object':
                    tasks_df["date"] = pd.to_datetime(tasks_df["date"], errors='coerce')
                
                # Group by date and count completed tasks
                completed_tasks = tasks_df[tasks_df["status"] == "Completed"]
                if not completed_tasks.empty:
                    # Group by date
                    completed_by_date = completed_tasks.groupby(completed_tasks["date"].dt.date).size()
                    
                    # Calculate productivity metrics
                    result = {
                        "total_completed": len(completed_tasks),
                        "completion_by_date": completed_by_date.to_dict(),
                        "average_daily_completion": completed_by_date.mean(),
                        "productivity_score": len(completed_tasks) / len(tasks_df) if len(tasks_df) > 0 else 0
                    }
                    
                    # Calculate productivity trend
                    if len(completed_by_date) > 1:
                        dates = sorted(completed_by_date.index)
                        if len(dates) > 5:
                            # Compare last 5 days to previous 5 days
                            recent = sum(completed_by_date[dates[-5:]])
                            previous = sum(completed_by_date[dates[-10:-5]])
                            
                            if previous > 0:
                                trend_pct = (recent - previous) / previous
                                result["trend"] = {
                                    "direction": "up" if trend_pct > 0 else "down",
                                    "percentage": abs(trend_pct) * 100
                                }
                    
                    return result
            
            # Fallback if required columns missing
            return {
                "productivity_score": 0,
                "message": "Required data missing for productivity analysis"
            }
            
        # AI-powered insights using OpenAI
        elif analysis_type == "ai_insights":
            prompt = self._create_insights_prompt(tasks_df, **kwargs)
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5
                )
                
                insights = response.choices[0].message.content
                
                return {
                    "insights": insights,
                    "task_count": len(tasks_df),
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except Exception as e:
                print(f"Error generating AI insights: {e}")
                return {
                    "error": str(e),
                    "message": "Unable to generate AI insights"
                }
                
        # Unknown analysis type
        return {
            "error": f"Unknown analysis type: {analysis_type}",
            "supported_types": ["basic", "productivity", "ai_insights"]
        }
    
    def _create_insights_prompt(self, tasks_df: pd.DataFrame, **kwargs) -> str:
        """
        Create a prompt for AI insights based on task data.
        
        Args:
            tasks_df: DataFrame of tasks.
            **kwargs: Additional arguments.
            
        Returns:
            str: The prompt.
        """
        person_name = kwargs.get("person_name", "the employee")
        
        # Convert DataFrame to a more readable format
        tasks_str = ""
        for _, row in tasks_df.iterrows():
            task_str = f"- {row.get('task', 'Unknown task')}"
            
            if 'status' in row:
                task_str += f" (Status: {row['status']})"
                
            if 'date' in row:
                date_str = row['date']
                if not isinstance(date_str, str):
                    date_str = date_str.strftime("%Y-%m-%d") if hasattr(date_str, 'strftime') else str(date_str)
                task_str += f" (Date: {date_str})"
                
            if 'category' in row:
                task_str += f" (Category: {row['category']})"
                
            tasks_str += task_str + "\n"
        
        # Basic statistics for the prompt
        basic_stats = self.analyze(tasks_df, analysis_type="basic")
        status_dist = basic_stats.get("status_distribution", {})
        completed = status_dist.get("Completed", 0)
        total = basic_stats.get("count", 0)
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        prompt = f"""
        You are CoachAI, a friendly and helpful workplace assistant who offers coaching insights in a conversational, supportive tone.
        
        ANALYZE THE FOLLOWING TASKS FOR {person_name}:
        
        {tasks_str}
        
        BASIC STATISTICS:
        - Total Tasks: {total}
        - Completion Rate: {completion_rate:.1f}%
        - Status Distribution: {status_dist}
        
        FIRST, ANALYZE THIS DATA TO IDENTIFY PATTERNS:
        - Task completion rates and patterns
        - Work distribution across different projects
        - Recent productivity trends
        - Task complexity and priority handling
        - Collaboration patterns
        
        THEN, PROVIDE INSIGHTS ON THE ANALYSIS IN A CONVERSATIONAL TONE, INCLUDING:
        1. A specific strength or accomplishment to recognize
        2. Specific instances that require immediate attention
        3. A friendly, practical, and tactical suggestion that could help them improve
        
        IMPORTANT STYLE GUIDANCE:
        - Write as a helpful colleague, not a formal report
        - Use personal language ("I notice...", "You're doing well at...")
        - Keep it brief and conversational (3-4 sentences per insight)
        - Avoid technical terms like "metadata analysis" or "velocity metrics"
        - Don't list categories like "STRENGTH:" or "OPPORTUNITY:" - just flow naturally
        - Sound encouraging and supportive throughout
        """
        
        return prompt

class ProjectAnalyzer(AnalyzerBase):
    """Analyzer for projects."""
    
    def analyze(self, 
                tasks: Union[List[Dict[str, Any]], pd.DataFrame],
                project: str,
                analysis_type: str = "health_check",
                **kwargs) -> Dict[str, Any]:
        """
        Analyze project health.
        
        Args:
            tasks: Tasks related to the project.
            project: Name of the project.
            analysis_type: Type of analysis to perform.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Analysis results.
        """
        # Convert list to DataFrame if necessary
        if isinstance(tasks, list):
            tasks_df = pd.DataFrame(tasks)
        else:
            tasks_df = tasks.copy()
            
        # Filter for the project if category is available
        if "category" in tasks_df.columns:
            project_tasks = tasks_df[tasks_df["category"] == project]
        else:
            project_tasks = tasks_df
            
        # Basic project health check
        if analysis_type == "health_check":
            # Calculate health metrics
            if project_tasks.empty:
                return {
                    "project": project,
                    "health_score": 0,
                    "message": "No tasks found for this project"
                }
                
            # Calculate basic metrics
            total_tasks = len(project_tasks)
            
            if "status" in project_tasks.columns:
                status_counts = project_tasks["status"].value_counts().to_dict()
                completed = status_counts.get("Completed", 0)
                blocked = status_counts.get("Blocked", 0)
                
                # Calculate health score (simple version)
                health_score = (completed / total_tasks * 100) - (blocked / total_tasks * 50)
                health_score = max(0, min(100, health_score))
                
                # Determine health status
                if health_score >= 75:
                    health_status = "Healthy"
                elif health_score >= 50:
                    health_status = "Needs Attention"
                else:
                    health_status = "At Risk"
                    
                return {
                    "project": project,
                    "health_score": health_score,
                    "health_status": health_status,
                    "task_count": total_tasks,
                    "status_distribution": status_counts
                }
            
            # Fallback if status column missing
            return {
                "project": project,
                "health_score": 50,  # Neutral score
                "health_status": "Unknown",
                "task_count": total_tasks,
                "message": "Limited data available for health assessment"
            }
            
        # AI-powered project insights
        elif analysis_type == "ai_insights":
            prompt = self._create_project_prompt(project_tasks, project, **kwargs)
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5
                )
                
                insights = response.choices[0].message.content
                
                return {
                    "project": project,
                    "insights": insights,
                    "task_count": len(project_tasks),
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            except Exception as e:
                print(f"Error generating project insights: {e}")
                return {
                    "project": project,
                    "error": str(e),
                    "message": "Unable to generate project insights"
                }
                
        # Unknown analysis type
        return {
            "project": project,
            "error": f"Unknown analysis type: {analysis_type}",
            "supported_types": ["health_check", "ai_insights"]
        }
    
    def _create_project_prompt(self, tasks_df: pd.DataFrame, project: str, **kwargs) -> str:
        """
        Create a prompt for AI project insights.
        
        Args:
            tasks_df: DataFrame of project tasks.
            project: Name of the project.
            **kwargs: Additional arguments.
            
        Returns:
            str: The prompt.
        """
        # Convert DataFrame to a more readable format
        tasks_str = ""
        for _, row in tasks_df.iterrows():
            task_str = f"- {row.get('task', 'Unknown task')}"
            
            if 'status' in row:
                task_str += f" (Status: {row['status']})"
                
            if 'employee' in row:
                task_str += f" (Employee: {row['employee']})"
                
            if 'date' in row:
                date_str = row['date']
                if not isinstance(date_str, str):
                    date_str = date_str.strftime("%Y-%m-%d") if hasattr(date_str, 'strftime') else str(date_str)
                task_str += f" (Date: {date_str})"
                
            tasks_str += task_str + "\n"
            
        # Basic statistics for the prompt
        task_count = len(tasks_df)
        
        # Status distribution
        status_dist = {}
        if 'status' in tasks_df.columns:
            status_dist = tasks_df["status"].value_counts().to_dict()
            
        # Employee distribution
        employee_dist = {}
        if 'employee' in tasks_df.columns:
            employee_dist = tasks_df["employee"].value_counts().to_dict()
        
        prompt = f"""
        You are ProjectAnalyst, a strategic advisor on project management and team productivity.

        ANALYZE PROJECT '{project}' TASKS:
        {tasks_str}

        PROJECT METADATA:
        - Total Tasks: {task_count}
        - Status Distribution: {status_dist}
        - Team Distribution: {employee_dist}

        FIRST, PERFORM A METADATA ANALYSIS ON THE PROJECT:
        - Calculate key project metrics: completion rate, velocity, team distribution
        - Identify how many tasks have been open for more than 7 days
        - Analyze distribution of task ages
        - Determine if certain team members have disproportionate workloads
        - Identify any bottlenecks or common blockers
        - Determine if task completion is on pace with creation

        THEN, PROVIDE A THREE-PART INSIGHT:
        1. HEALTH STATUS: One sentence on overall project health
        2. KEY RISK: The most critical item requiring attention
        3. STRATEGIC RECOMMENDATION: One specific action to improve project health

        Keep your response focused, data-driven, and immediately actionable.
        """
        
        return prompt