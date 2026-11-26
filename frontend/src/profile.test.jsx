import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { Profile } from './App';

const snapshot = JSON.parse(readFileSync(new URL('../public/data/serie-a-2026.json', import.meta.url), 'utf8'));

describe('Profile snapshot metrics', () => {
  it('shows xG from metric id 26 even when the catalog has fewer than 27 entries', () => {
    const data = structuredClone(snapshot);
    const player = data.players.find(p => p.s['26'] > 0 && p.minutes >= 450);
    player.s['26'] = 12.34;
    const html = renderToStaticMarkup(<Profile data={data} playerId={player.id} onChoose={() => {}} />);
    expect(html).toMatch(/Gols esperados \/ xG[\s\S]*?kpi-number">12,34</);
    expect(html).toContain('— jogos');
    expect(html).toContain('— titularidades');
  });

  it('keeps unavailable xG distinct from a real zero', () => {
    const data = structuredClone(snapshot);
    const player = data.players[0];
    delete player.s['26'];
    let html = renderToStaticMarkup(<Profile data={data} playerId={player.id} onChoose={() => {}} />);
    expect(html).toMatch(/Gols esperados \/ xG[\s\S]*?kpi-number">—</);
    player.s['26'] = 0;
    html = renderToStaticMarkup(<Profile data={data} playerId={player.id} onChoose={() => {}} />);
    expect(html).toMatch(/Gols esperados \/ xG[\s\S]*?kpi-number">0</);
  });
});
