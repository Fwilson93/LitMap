@classmethod
def create(cls, title: str, description: str = "") -> "Project":
    project = cls(
        project_id=slugify(title),
        title=title,
        description=description,
    )

    project.timeline.append(
        TimelineEvent(
            event_type="project_created",
            message=f"Created project '{title}'.",
            payload={"title": title},
        )
    )

    return project


def touch(self) -> None:
    self.updated_at = utc_now()


def candidate_map(self) -> dict[str, Candidate]:
    return {candidate.candidate_id: candidate for candidate in self.candidates}

