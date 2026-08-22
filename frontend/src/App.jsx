import { useCallback, useRef, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import Hero from "./components/Hero.jsx";
import Programs from "./components/Programs.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import Faq from "./components/Faq.jsx";
import Footer from "./components/Footer.jsx";
import { askQuestion } from "./lib/api.js";

let nextId = 1;

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const chatSectionRef = useRef(null);

  const scrollToChat = useCallback(() => {
    document.getElementById("chat")?.closest("section")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const send = useCallback(async (question) => {
    setError(null);
    setMessages((prev) => [...prev, { id: nextId++, role: "user", text: question }]);
    setIsSending(true);

    try {
      const answer = await askQuestion(question);
      setMessages((prev) => [...prev, { id: nextId++, role: "assistant", text: answer }]);
    } catch (err) {
      const msg =
        err.name === "AbortError"
          ? null
          : err.message === "Failed to fetch"
            ? "Could not reach the assistant backend"
            : err.message;
      if (msg) {
        setError(msg);
        setMessages((prev) => [
          ...prev,
          {
            id: nextId++,
            role: "assistant",
            error: true,
            text: `Sorry, something went wrong while answering. (${msg})`,
          },
        ]);
      }
    } finally {
      setIsSending(false);
    }
  }, []);

  const quickAsk = useCallback(
    (question) => {
      scrollToChat();
      if (!isSending) send(question);
    },
    [isSending, scrollToChat, send],
  );

  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar onAskClick={scrollToChat} />
      <main>
        <Hero chatProps={{ messages, isSending, error, onSend: send }} />
        <Programs onQuickAsk={quickAsk} />
        <HowItWorks />
        <Faq />
      </main>
      <Footer onAskClick={scrollToChat} />
    </div>
  );
}
