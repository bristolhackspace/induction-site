from typing import OrderedDict
from flask import Flask, render_template, request
from bristolhackspace.theme import theme_blueprint
import attr
import re
import random

app = Flask(__name__)
app.register_blueprint(theme_blueprint, url_prefix="/theme")

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


@attr.s
class Question:
    text = attr.ib()
    answers = attr.ib()


@attr.s
class Answer:
    text = attr.ib()
    correct = attr.ib(default=False)


questionnaire = Questionnaire(
    questions=[
        Question(
            "What should you not be?",
            answers=[
                Answer("On fire", correct=True),
                Answer("Cool"),
                Answer("Nerdy"),
            ],
        )
    ]
)


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


@app.route("/", methods=["GET", "POST"])
def index():
    if "submitted" in request.form:
        response = parse_response(request.form)
        question_order = response.keys()
        validity = questionnaire.validate_answers(response)
        all_correct = False not in validity
    else:
        response = {}
        question_order = random.sample(
            range(len(questionnaire.questions)), k=len(questionnaire.questions)
        )
        validity = [None] * len(questionnaire.questions)
        pass

    answer_order = {}
    for i, question in enumerate(questionnaire.questions):
        num_answers = len(question.answers)
        answer_order[i] = random.sample(range(num_answers), k=num_answers)

    return render_template(
        "index.html",
        questionnaire=questionnaire,
        question_order=question_order,
        answer_order=answer_order,
        validity=validity,
        response=response,
    )
