from typing import OrderedDict
from flask import Flask, render_template, request, abort, session
from bristolhackspace.theme import theme_blueprint
from bristolhackspace.sso import BaseDiscourseSSO
from bristolhackspace.discourse import DiscourseClient
import attr
import re
import random
import json
from requests.models import HTTPError

app = Flask(__name__)
app.config.from_envvar('INDUCTIONSITE_SETTINGS')
app.register_blueprint(theme_blueprint, url_prefix="/theme")
sso = BaseDiscourseSSO(app.config["DISCOURSE_CONNECT_PROVIDER_SECRET"], app.config["DISCOURSE_URL"])
dc_client = DiscourseClient(app.config["DISCOURSE_URL"], app.config["DISCOURSE_API_USER"], app.config["DISCOURSE_API_KEY"])
QUESTION_REGEX = re.compile(r"^question_(\d+)$")


@attr.s
class Questionnaire:
    questions = attr.ib()

    def validate_answers(self, answers):
        correct = [False] * len(self.questions)

        for q, a in answers.items():
            try:
                question = self.questions[q]
                if question.answers[a].correct:
                    correct[q] = True
            except IndexError:
                pass

        return correct

    @classmethod
    def from_json(cls, json):
        questions = [Question.from_json(q_json) for q_json in json["questions"]]
        return cls(questions)


@attr.s
class Question:
    text = attr.ib()
    answers = attr.ib()
    answer_hint = attr.ib()

    @classmethod
    def from_json(cls, json):
        text = json["text"]
        answers = [Answer.from_json(a_json) for a_json in json["answers"]]
        answer_hint = json["answer_hint"]
        return cls(text, answers, answer_hint)


@attr.s
class Answer:
    text = attr.ib()
    correct = attr.ib(default=False)

    @classmethod
    def from_json(cls, json):
        text = json["text"]
        correct = bool(json.get("correct", False))
        return cls(text, correct)


def parse_response(form):
    answers = OrderedDict()
    for k, v in form.items():
        try:
            q_match = QUESTION_REGEX.match(k)
            if q_match:
                answers[int(q_match.group(1))] = int(v)
        except Exception:
            pass
    return answers


def load_questionnaire(name):
    try:
        with app.open_resource(f"questions/{name}.json", "r") as fh:
            data = json.load(fh)
            return Questionnaire.from_json(data)
    except FileNotFoundError:
        abort(404) 


def add_logged_in_user_to_group(group_name):
    group = dc_client.group(group_name)
    group_id = group["group"]["id"]
    try:
        dc_client.add_group_member(group_id, session["username"])
    except HTTPError as ex:
        if ex.response.status_code != 422:
            raise


def is_already_member(group_name):
    user = dc_client.user_by_id(session["member_id"])
    group = dc_client.group(group_name)
    group_id = group["group"]["id"]

    for group in user["groups"]:
        if group["id"] == group_id:
            return True
    return False


@app.route("/<questionaire_name>")
@sso.requires_login
def index(questionaire_name):
    questionnaire = load_questionnaire(questionaire_name)
    question_order = random.sample(
        range(len(questionnaire.questions)), k=len(questionnaire.questions)
    )

    answer_order = {}
    for i, question in enumerate(questionnaire.questions):
        num_answers = len(question.answers)
        answer_order[i] = random.sample(range(num_answers), k=num_answers)

    return render_template(
        "index.html",
        questionaire_name=questionaire_name,
        questionnaire=questionnaire,
        question_order=question_order,
        answer_order=answer_order,
    )


@app.route("/<questionaire_name>/validate", methods=["POST"])
def validate(questionaire_name):
    questionnaire = load_questionnaire(questionaire_name)
    response = parse_response(request.form)
    validity = questionnaire.validate_answers(response)
    all_correct = False not in validity
    if all_correct:
        add_logged_in_user_to_group(f"{questionaire_name}_inducted")

    wrong_answers = []
    for i, valid in enumerate(validity):
        if not valid:
            wrong_answers.append(i)

    return render_template(
        "verify.html",
        questionaire_name=questionaire_name,
        all_correct=all_correct,
        wrong_answers=wrong_answers,
        questionnaire=questionnaire
    )

    