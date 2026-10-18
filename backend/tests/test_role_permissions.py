from app.core.permissions import effective_roles


def test_student_has_only_student_features():
    assert effective_roles(["STUDENT"]) == {"STUDENT"}


def test_faculty_inherits_student_features():
    assert effective_roles(["FACULTY"]) == {"STUDENT", "FACULTY"}


def test_welfare_inherits_faculty_and_student_features():
    assert effective_roles(["WELFARE"]) == {"STUDENT", "FACULTY", "WELFARE"}


def test_director_inherits_lower_feature_roles():
    assert effective_roles(["DIRECTOR"]) == {"STUDENT", "FACULTY", "WELFARE", "DIRECTOR"}


def test_events_office_inherits_all_workflow_features():
    assert effective_roles(["EVENTS"]) == {"STUDENT", "FACULTY", "WELFARE", "DIRECTOR", "EVENTS"}


def test_admin_does_not_gain_workflow_roles_implicitly():
    assert effective_roles(["ADMIN"]) == {"ADMIN"}
