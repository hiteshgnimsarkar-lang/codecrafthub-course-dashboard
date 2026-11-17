"""
Simple Flask REST API for managing courses.

The API stores course data in a JSON file named courses.json.

Available endpoints:
    POST   /api/courses
    GET    /api/courses
    GET    /api/courses/<course_id>
    PUT    /api/courses/<course_id>
    DELETE /api/courses/<course_id>
"""

import json
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request


app = Flask(__name__)

# Store courses.json in the same directory as this Python file.
COURSES_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "courses.json"
)

# A lock helps prevent two requests from writing to the file at the same time.
file_lock = threading.RLock()

# Allowed course status values.
ALLOWED_STATUSES = {
    "Not Started",
    "In Progress",
    "Completed",
}

# Required fields supplied by users.
REQUIRED_FIELDS = [
    "name",
    "description",
    "target_date",
    "status",
]


class StorageError(Exception):
    """Custom exception used for file read/write errors."""
    pass


def error_response(message, status_code):
    """Return a consistent JSON error response."""
    return jsonify({
        "error": message
    }), status_code


def ensure_courses_file():
    """
    Create courses.json automatically if it does not already exist.

    The file is initialized with an empty JSON list.
    """
    with file_lock:
        if not os.path.exists(COURSES_FILE):
            try:
                with open(COURSES_FILE, "w", encoding="utf-8") as file:
                    json.dump([], file, indent=2)
                    file.write("\n")
            except OSError as error:
                raise StorageError(
                    f"Unable to create courses.json: {error}"
                ) from error


def read_courses():
    """
    Read all courses from courses.json.

    Returns:
        list: A list of course dictionaries.

    Raises:
        StorageError: If the file cannot be read or contains invalid data.
    """
    ensure_courses_file()

    with file_lock:
        try:
            with open(COURSES_FILE, "r", encoding="utf-8") as file:
                courses = json.load(file)
        except json.JSONDecodeError as error:
            raise StorageError(
                "courses.json contains invalid JSON."
            ) from error
        except OSError as error:
            raise StorageError(
                f"Unable to read courses.json: {error}"
            ) from error

    # The JSON file must contain a list of courses.
    if not isinstance(courses, list):
        raise StorageError(
            "courses.json must contain a JSON list."
        )

    return courses


def write_courses(courses):
    """
    Write the supplied list of courses to courses.json.

    Raises:
        StorageError: If the file cannot be written.
    """
    with file_lock:
        try:
            with open(COURSES_FILE, "w", encoding="utf-8") as file:
                json.dump(courses, file, indent=2)
                file.write("\n")
        except OSError as error:
            raise StorageError(
                f"Unable to write courses.json: {error}"
            ) from error


def get_next_course_id(courses):
    """
    Generate the next course ID.

    IDs start at 1. The next ID is one greater than the current
    highest ID in the file.
    """
    if not courses:
        return 1

    try:
        ids = []

        for course in courses:
            if not isinstance(course, dict):
                raise ValueError

            course_id = course.get("id")

            # Boolean values are technically integers in Python,
            # but they should not be accepted as course IDs.
            if isinstance(course_id, bool) or not isinstance(course_id, int):
                raise ValueError

            ids.append(course_id)

        return max(ids, default=0) + 1

    except (ValueError, TypeError):
        raise StorageError(
            "courses.json contains an invalid course ID."
        )


def validate_course_data(data, require_all_fields=True):
    """
    Validate course data supplied by the client.

    Args:
        data (dict): JSON data from the request.
        require_all_fields (bool): Whether all required fields must exist.

    Returns:
        tuple: (validated_data, error_message)

    The returned error_message is None when validation succeeds.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    if require_all_fields:
        missing_fields = [
            field for field in REQUIRED_FIELDS
            if field not in data
        ]

        if missing_fields:
            return None, (
                "Missing required field(s): "
                + ", ".join(missing_fields)
            )

    # For PUT, this implementation requires all fields. This ensures
    # every saved course always contains all required properties.
    for field in REQUIRED_FIELDS:
        if field not in data:
            continue

        value = data[field]

        if not isinstance(value, str) or not value.strip():
            return None, f"'{field}' must be a non-empty string."

    # Validate target_date using the exact YYYY-MM-DD format.
    if "target_date" in data:
        target_date = data["target_date"]

        try:
            parsed_date = datetime.strptime(
                target_date,
                "%Y-%m-%d"
            )

            # This additional check rejects values such as
            # 2025-1-1, even though some parsers may accept them.
            if parsed_date.strftime("%Y-%m-%d") != target_date:
                return None, (
                    "'target_date' must use the format YYYY-MM-DD."
                )

        except ValueError:
            return None, (
                "'target_date' must be a valid date in "
                "YYYY-MM-DD format."
            )

    # Validate status against the allowed values.
    if "status" in data and data["status"] not in ALLOWED_STATUSES:
        return None, (
            "'status' must be one of: "
            + ", ".join(sorted(ALLOWED_STATUSES))
        )

    # Return only fields that clients are allowed to provide.
    cleaned_data = {
        field: data[field]
        for field in REQUIRED_FIELDS
        if field in data
    }

    return cleaned_data, None


def get_json_body():
    """
    Safely read a JSON request body.

    Returns:
        tuple: (body, error_message)
    """
    if not request.is_json:
        return None, "Request body must use Content-Type: application/json."

    try:
        body = request.get_json(silent=False)
    except Exception:
        return None, "Request body contains invalid JSON."

    return body, None


@app.before_request
def create_storage_file_before_request():
    """
    Make sure courses.json exists before handling every request.

    This allows file creation errors to be returned as JSON API responses.
    """
    try:
        ensure_courses_file()
    except StorageError as error:
        return error_response(str(error), 500)


@app.route("/api/courses", methods=["POST"])
def create_course():
    """Add a new course."""
    body, body_error = get_json_body()

    if body_error:
        return error_response(body_error, 400)

    course_data, validation_error = validate_course_data(
        body,
        require_all_fields=True
    )

    if validation_error:
        return error_response(validation_error, 400)

    try:
        courses = read_courses()

        new_course = {
            "id": get_next_course_id(courses),
            "name": course_data["name"].strip(),
            "description": course_data["description"].strip(),
            "target_date": course_data["target_date"],
            "status": course_data["status"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        courses.append(new_course)
        write_courses(courses)

        return jsonify(new_course), 201

    except StorageError as error:
        return error_response(str(error), 500)


@app.route("/api/courses", methods=["GET"])
def get_all_courses():
    """Return all courses."""
    try:
        courses = read_courses()
        return jsonify(courses), 200

    except StorageError as error:
        return error_response(str(error), 500)


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    """Return one course by ID."""
    try:
        courses = read_courses()

        for course in courses:
            if course.get("id") == course_id:
                return jsonify(course), 200

        return error_response("Course not found.", 404)

    except StorageError as error:
        return error_response(str(error), 500)


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    """
    Update an existing course.

    PUT requires all user-editable fields:
    name, description, target_date, and status.

    The id and created_at values cannot be changed by the client.
    """
    body, body_error = get_json_body()

    if body_error:
        return error_response(body_error, 400)

    course_data, validation_error = validate_course_data(
        body,
        require_all_fields=True
    )

    if validation_error:
        return error_response(validation_error, 400)

    try:
        courses = read_courses()

        for index, course in enumerate(courses):
            if course.get("id") == course_id:
                updated_course = {
                    "id": course["id"],
                    "name": course_data["name"].strip(),
                    "description": course_data["description"].strip(),
                    "target_date": course_data["target_date"],
                    "status": course_data["status"],
                    # Preserve the original creation timestamp.
                    "created_at": course.get("created_at"),
                }

                courses[index] = updated_course
                write_courses(courses)

                return jsonify(updated_course), 200

        return error_response("Course not found.", 404)

    except StorageError as error:
        return error_response(str(error), 500)


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    """Delete a course by ID."""
    try:
        courses = read_courses()

        for index, course in enumerate(courses):
            if course.get("id") == course_id:
                deleted_course = courses.pop(index)
                write_courses(courses)

                return jsonify({
                    "message": "Course deleted successfully.",
                    "course": deleted_course,
                }), 200

        return error_response("Course not found.", 404)

    except StorageError as error:
        return error_response(str(error), 500)

@app.route("/api/courses/stats", methods=["GET"])
def get_course_statistics():
    """
    Return statistics about all courses.

    The response includes:
    - Total number of courses
    - Number of courses in each supported status
    """
    try:
        courses = read_courses()

        # Start every status at zero so statuses with no courses
        # are still included in the response.
        courses_by_status = {
            "Not Started": 0,
            "In Progress": 0,
            "Completed": 0,
        }

        # Count each course according to its status.
        for course in courses:
            status = course.get("status")

            if status in courses_by_status:
                courses_by_status[status] += 1

        return jsonify({
            "total_courses": len(courses),
            "courses_by_status": courses_by_status,
        }), 200

    except StorageError as error:
        return error_response(str(error), 500)

@app.errorhandler(404)
def handle_404(error):
    """Return JSON instead of Flask's default HTML 404 response."""
    return error_response("Endpoint not found.", 404)


@app.errorhandler(405)
def handle_405(error):
    """Return JSON instead of Flask's default HTML 405 response."""
    return error_response("HTTP method not allowed.", 405)



if __name__ == "__main__":
    # debug=True is useful while learning, but should be disabled in production.
    app.run(debug=True)