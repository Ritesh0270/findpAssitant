from flask import Flask, render_template, request, jsonify
from aichat import FindProsAssistant

app = Flask(__name__, template_folder="templates")

assistant = FindProsAssistant()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}

        query = (data.get("query") or data.get("message") or "").strip()
        chat_history = data.get("chat_history", [])

        if not query:
            return jsonify({
                "answer": "Please enter a query.",
                "references": [],
                "recommendations": [],
                "top_result": None,
                "status": "empty_query"
            }), 400

        result = assistant.reply(query, chat_history)

        if not isinstance(result, dict):
            return jsonify({
                "answer": str(result),
                "references": [],
                "recommendations": [],
                "top_result": None,
                "status": "unexpected_result"
            })

        references = result.get("references", [])
        recommendations = result.get("recommendations", [])
        top_result = result.get("top_result")
        status = result.get("status", "success")

        cleaned_references = []
        for ref in references:
            cleaned_references.append({
                "ref": ref.get("ref"),
                "id": ref.get("id"),
                "task": ref.get("task", "Service"),
                "type": ref.get("type", "task"),
                "url": ref.get("url", "")
            })

        cleaned_recommendations = []
        for item in recommendations:
            cleaned_recommendations.append({
                "id": item.get("id"),
                "task": item.get("task", "Service"),
                "type": item.get("type", "task"),
                "url": item.get("url", "")
            })

        cleaned_top_result = None
        if isinstance(top_result, dict):
            cleaned_top_result = {
                "id": top_result.get("id"),
                "task": top_result.get("task", "Service"),
                "type": top_result.get("type", "task"),
                "url": top_result.get("url", "")
            }

        return jsonify({
            "answer": result.get("answer", "No answer found."),
            "references": cleaned_references,
            "recommendations": cleaned_recommendations,
            "top_result": cleaned_top_result,
            "status": status
        })

    except Exception as e:
        print("Error in /chat route:", e)
        return jsonify({
            "answer": f"Server error: {str(e)}",
            "references": [],
            "recommendations": [],
            "top_result": None,
            "status": "server_error"
        }), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)