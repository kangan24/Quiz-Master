from dotenv import load_dotenv
import os
from google import genai
import json
from datetime import datetime
import pandas as pd

import streamlit as st

st.set_option(
    "client.showErrorDetails",
    False
)

st.set_page_config(
    page_title="Quiz Master",
    page_icon="🤖",
    layout="wide"
) 


st.markdown("""
<style>

.main {
    padding-top: 1rem;
}

h1 {
    text-align: center;
    color: #FFD700;
}

.stButton > button {
    width: 100%;
    height: 3em;
    font-size: 18px;
    font-weight: bold;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Gemini API key not found.")
    st.stop()
client = genai.Client(api_key=api_key)


# Session State
if "quiz" not in st.session_state:
    st.session_state.quiz = None

if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

if "score" not in st.session_state:
    st.session_state.score = 0

if "percentage" not in st.session_state:
    st.session_state.percentage = 0

if "feedback" not in st.session_state:
    st.session_state.feedback = ""

if "history_saved" not in st.session_state:
    st.session_state.history_saved = False

if "current_question" not in st.session_state:
    st.session_state.current_question = 0

if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}

if "timer_started" not in st.session_state:
    st.session_state.timer_started = False

if "quiz_start_time" not in st.session_state:
    st.session_state.quiz_start_time = None


# Generate Quiz
def generate_quiz(topic, difficulty, num_questions):

    prompt = f"""
    Generate exactly {num_questions} MCQ questions about {topic}.

    Difficulty: {difficulty}

    IMPORTANT:
    - Randomize the correct answer position.
    - The correct answer must NOT always be A.
    - Distribute answers across A, B, C, and D.
    - Make incorrect options plausible.
    - Do not follow predictable answer patterns.

    Return ONLY valid JSON in this format:

    [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "answer": "A",
            "explanation": "Explanation here in exactly 1 or 2 lines"
        }}
    ]
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
    except Exception as e:
        error_text = str(e)
        if "RESOURCE_EXHAUSTED" in error_text:
            st.error(
                "⚠️ Gemini API quota exceeded. Please try again later."
            )
        else:
            st.error(
                "⚠️ Unable to generate quiz right now."
            )
        return []

    try:
        quiz = json.loads(response.text)
        return quiz

    except json.JSONDecodeError:
        st.error("Failed to parse quiz data.")
        return []


#  AI Feedback
def generate_feedback(topic, difficulty, score, total_questions):

    percentage = (score / total_questions) * 100

    report_prompt = f"""
    The user completed a quiz.

    Topic: {topic}
    Difficulty: {difficulty}

    Score: {score}/{total_questions}
    Percentage: {percentage:.2f}%

    Provide:
    1. A short performance review.
    2. Strengths.
    3. Areas to improve.

    Keep it under 100 words point wise.
    """

    try:
        report = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=report_prompt
        )
        return report.text

    except Exception:
        return """
        ⚠️ AI Feedback is currently unavailable.
        Please try again later.
        """


# STREAMLIT UI

st.sidebar.title("🎯 Quiz Master")

page = st.sidebar.radio(
    "🎮 Menu",
    ["🏆 Quiz Arena", "📊 Hall of Fame"]
)


# HISTORY PAGE
if page == "📊 Hall of Fame":

    st.title("📊 Quiz History")
    st.caption("Track your quiz performance over time")

    try:

        rows = []

        with open("quiz_history.txt", "r") as file:

            for line in file:

                parts = line.strip().split(" | ")

                if len(parts) == 5:

                    rows.append(parts)

        if rows:

            df = pd.DataFrame(
                rows,
                columns=[
                    "Date",
                    "Topic",
                    "Difficulty",
                    "Score",
                    "Percentage"
                ]
            )
            df = df.iloc[::-1].reset_index(drop=True)

            best_score = max(
                float(str(x).replace("%", ""))
                for x in df["Percentage"]
            )

            avg_score = sum(
                float(str(x).replace("%", ""))
                for x in df["Percentage"]
            ) / len(df)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Quizzes",
                    len(df)
                )

            with col2:
                st.metric(
                    "Best Score",
                    f"{best_score:.2f}%"
                )

            with col3:
                st.metric(
                    "Average Score",
                    f"{avg_score:.2f}%"
                )

            st.dataframe(
                df,
                use_container_width=True
            )

        else:
            st.info("No quiz attempts yet.")

    except FileNotFoundError:
        st.info("No quiz history found.")

    st.stop()


# QUIZ PAGE

st.title("🏆 QUIZ CHALLENGE")

st.markdown("""
### 🎯 Test your knowledge on ANY topic!

Choose a topic, challenge yourself,
and see if you can become the Quiz Champion.
""")

topic = st.text_input(
    "📚 Choose Your Quiz Topic",
    key="topic_input"
)

difficulty = st.selectbox(
    "🎮 Select Difficulty",
    ["Easy", "Medium", "Hard"],
    key="difficulty_input"
)

num_questions = st.slider(
    "📝 Number of Questions",
    min_value=5,
    max_value=20,
    value=5,
    step=1,
    key="num_questions_input"
)

quiz_time = st.selectbox(
    "⏱ Quiz Time Limit",
    [1, 2, 5, 10, 15],
    index=2
)

# Generate Quiz
if st.button("Generate Quiz"):
    if not topic:
        st.warning("Please enter a topic.")
    else:
        with st.spinner("Generating Quiz..."):

            st.session_state.quiz = generate_quiz(
                topic,
                difficulty,
                num_questions
            )

            st.session_state.quiz_submitted = False
            st.session_state.score = 0
            st.session_state.percentage = 0
            st.session_state.feedback = ""
            st.session_state.history_saved = False
            st.session_state.current_question = 0
            st.session_state.user_answers = {}

            st.session_state.timer_started = True
            st.session_state.quiz_start_time = datetime.now()
            st.session_state.quiz_time_limit = quiz_time


# Display Quiz
if st.session_state.quiz and not st.session_state.quiz_submitted:

    current = st.session_state.current_question
    
    elapsed = (
        datetime.now() -
        st.session_state.quiz_start_time
    ).total_seconds()

    remaining = (
        st.session_state.quiz_time_limit * 60
    ) - elapsed

    if remaining <= 0:

        st.warning(
            "⏰ Time is up! Quiz submitted automatically."
        )

        st.session_state.quiz_submitted = True
        st.rerun()

    mins = int(remaining // 60)
    secs = int(remaining % 60)

    st.metric(
        "⏱ Time Remaining",
        f"{mins:02d}:{secs:02d}"
    )

    q = st.session_state.quiz[current]

    st.progress(
        (current + 1) / len(st.session_state.quiz)
    )

    st.subheader(
        f"Question {current + 1}/{len(st.session_state.quiz)}"
    )

    st.write(q["question"])

    saved_answer = st.session_state.user_answers.get(
        current,
        None
    )

    options = list(q["options"].keys())

    answer = st.radio(
        "Choose your answer:",
        options=options,
        format_func=lambda x:
            f"{x}. {q['options'][x]}",
        key=f"question_{current}",
        index=(
            options.index(saved_answer)
            if saved_answer in options
            else None
        )
    )

    if answer is not None:
        st.session_state.user_answers[current] = answer

    col1, col2 = st.columns(2)

    with col1:

        if current > 0:

            if st.button("⬅ Previous"):

                st.session_state.current_question -= 1

                st.rerun()

    with col2:

        if current < len(st.session_state.quiz) - 1:

            if st.button("Next ➡"):

                if answer is None:

                    st.warning(
                        "Please select an answer."
                    )

                else:

                    st.session_state.current_question += 1
                    st.rerun()

        else:

            if st.button("🏁 Finish Quiz"):

                if answer is None:

                    st.warning(
                        "Please select an answer."
                    )

                else:
                    st.session_state.quiz_submitted = True
                    st.rerun()


# results
if st.session_state.quiz_submitted:
    score = 0
    st.subheader("Results")

    for i, q in enumerate(
        st.session_state.quiz,
        start=1
    ):
        user_answer = st.session_state.user_answers.get(
            i - 1,
            "Not Answered"
        )

        if user_answer == q["answer"]:
            score += 1
            st.success(
                f"Question {i}: Correct"
            )
        else:
            st.error(
                f"Question {i}: Wrong"
            )
        st.write(
            f"Your Answer: {user_answer}"
        )
        st.write(
            f"Correct Answer: {q['answer']}"
        )
        st.info(
            f"Explanation: {q['explanation']}"
        )

    st.session_state.score = score

    st.session_state.percentage = (
        score / len(st.session_state.quiz)
    ) * 100

    st.markdown("---")

    st.metric(
        "🏆 Final Score",
        f"{st.session_state.percentage:.2f}%"
    )
    if st.session_state.percentage >= 80:
        st.balloons()
        st.success(
            "🏆 QUIZ CHAMPION!"
        )

    elif st.session_state.percentage >= 60:
        st.success(
            "🎉 Great Job!"
        )

    else:
        st.warning(
            "💪 Keep Practicing!"
        )
    

    # feedback
    if not st.session_state.feedback:
        with st.spinner(
            "Generating AI Feedback..."
        ):
            st.session_state.feedback = generate_feedback(
                topic,
                difficulty,
                score,
                len(st.session_state.quiz)
            )

    st.subheader("🤖 AI Feedback")

    st.write(st.session_state.feedback)

    st.markdown("---")

    
    # history
    if not st.session_state.history_saved:
        with open("quiz_history.txt", "a") as file:

            file.write(
                f"{datetime.now():%Y-%m-%d %H:%M} | "
                f"{topic} | "
                f"{difficulty} | "
                f"{score}/{len(st.session_state.quiz)} | "
                f"{st.session_state.percentage:.2f}%\n"
            )
        st.session_state.history_saved = True


    # new quiz
    if st.button("🔄 Start New Quiz"):

        st.session_state.quiz = None
        st.session_state.quiz_submitted = False
        st.session_state.score = 0
        st.session_state.percentage = 0
        st.session_state.feedback = ""
        st.session_state.history_saved = False
        st.session_state.current_question = 0
        st.session_state.user_answers = {}

        st.session_state.timer_started = False
        st.session_state.quiz_start_time = None

        keys_to_remove = [
            key
            for key in list(st.session_state.keys())
            if key.startswith("question_")
        ]
        for key in keys_to_remove:
            del st.session_state[key]

        for key in [
            "topic_input",
            "difficulty_input",
            "num_questions_input"
        ]:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()