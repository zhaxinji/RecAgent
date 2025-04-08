try:
    from .user import User, APIKey
    from .paper import Paper, Tag, Note
    from .experiment import Experiment, ExperimentRun, ExperimentStatus
    from .writing import WritingProject, WritingSection, WritingReference, ProjectStatus
except ImportError:
    from agent_rec.src.models.user import User, APIKey
    from agent_rec.src.models.paper import Paper, Tag, Note
    from agent_rec.src.models.experiment import Experiment, ExperimentRun, ExperimentStatus
    from agent_rec.src.models.writing import WritingProject, WritingSection, WritingReference, ProjectStatus
from src.models.paper import Paper, Tag, Note
from src.models.experiment import Experiment, ExperimentRun, ExperimentStatus
from src.models.writing import WritingProject, WritingSection, WritingReference, ProjectStatus 