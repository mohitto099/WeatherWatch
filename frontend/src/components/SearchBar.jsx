import { useState } from "react";

const SUGGESTIONS = ["Mumbai", "London", "Tokyo", "New York"];

export default function SearchBar({ onSearch, busy }) {
  const [value, setValue] = useState("");

  const submit = (e) => {
    e.preventDefault();
    onSearch(value);
  };

  return (
    <div className="search">
      <form onSubmit={submit} className="search-row">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Search a city, e.g. Mumbai"
          aria-label="City name"
          maxLength={100}
        />
        <button type="submit" disabled={busy || !value.trim()}>
          {busy ? "Working..." : "Get weather"}
        </button>
      </form>
      <div className="chips">
        <span>Try:</span>
        {SUGGESTIONS.map((c) => (
          <button
            key={c}
            type="button"
            className="chip"
            disabled={busy}
            onClick={() => {
              setValue(c);
              onSearch(c);
            }}
          >
            {c}
          </button>
        ))}
      </div>
    </div>
  );
}
