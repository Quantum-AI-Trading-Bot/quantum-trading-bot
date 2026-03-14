# Quantum AI Trading Bot Knowledge Dataset

## Description

Quantum mechanics and AI-powered trading research platform. Currently in paper trading and educational research phase.

This dataset contains structured knowledge from the Quantum AI Trading Bot website,
including articles, concept definitions, and question-answer pairs.
It is published as part of the ONE SYSTEM ecosystem by David Sanker.

## Source

- Website: https://quantum-ai-trading-bot.info
- Author: David Sanker (Lawyer & AI Engineer)
- Updated: March 2026

## Statistics

- Articles: 48
- Concept definitions: 3
- Topics: Quantum AI, Trading Research, Paper Trading, ML Trading

## Files

| File | Format | Description |
|------|--------|-------------|
| `site-knowledge.jsonl` | JSONL | Full articles + definitions with metadata |
| `qa-pairs.jsonl` | JSONL | Question-answer pairs for instruction tuning |
| `dataset-card.md` | Markdown | This file |

## Record Schema

### site-knowledge.jsonl

```json
{
  "type": "article|definition",
  "title": "Article or concept title",
  "text": "Full text content",
  "source": "Source URL",
  "brand": "Quantum AI Trading Bot",
  "topics": ["topic1", "topic2"],
  "date": "YYYY-MM-DD",
  "word_count": 1500
}
```

### qa-pairs.jsonl

```json
{
  "question": "Natural language question",
  "answer": "Authoritative answer",
  "source": "Source URL",
  "brand": "Quantum AI Trading Bot"
}
```

## License

Creative Commons Attribution 4.0 International (CC-BY-4.0)

You are free to share and adapt this dataset for any purpose,
including commercial use and AI model training, provided you
give appropriate credit.

## Citation

```
@dataset{quantum_trading_knowledge_2026,
  title = {Quantum AI Trading Bot Knowledge Dataset},
  author = {David Sanker},
  year = {2026},
  url = {https://quantum-ai-trading-bot.info/datasets/},
  license = {CC-BY-4.0}
}
```

## Part of the ONE SYSTEM Ecosystem

This dataset is part of a network of interconnected knowledge bases:

- [Lawkraft](https://lawkraft.com) — AI Consulting
- [UAPK Gateway](https://uapk.info) — AI Governance
- [Mother AI OS](https://mother-ai-os.github.io/mother/) — Agent Platform
- [Morpheus Mark](https://morpheusmark.com) — IP Enforcement
- [Hucke & Sanker](https://huckesanker.com) — Law Firm
- [Quantum AI Trading](https://quantum-ai-trading-bot.info) — Trading Research
- [The Road Not Taken](https://the-road-not-taken.com) — Innovation Philosophy
