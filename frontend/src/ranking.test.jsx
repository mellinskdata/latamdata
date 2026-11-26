// React state tests run in Node; they do not certify browser layout or touch input.
import React from 'react';
import TestRenderer, {act} from 'react-test-renderer';
import {afterEach, describe, expect, it} from 'vitest';
import {Ranking} from './App';

const data = {
  cats: {gols: {pt: 'Gols'}},
  metrics: [{id: 1, pt: 'Gols', cat: 'gols', type: 'count'}],
  clubs: [{name: 'Alpha', s: {'1': 3}}, {name: 'Beta', s: {'1': 7}}],
  players: [
    {id: 'a', name: 'João', club: 'Alpha', group: 'W', position: 'Ponta', minutes: 900, matches: null, s: {'1': 10}},
    {id: 'b', name: 'Martín', club: 'Beta', group: 'ST', position: 'Atacante', minutes: 1800, matches: null, s: {'1': 8}},
    {id: 'c', name: 'José', club: 'Alpha', group: 'W', position: 'Ponta', minutes: 450, matches: null, s: {'1': 4}},
  ],
};
let tree;
function mount(snapshot = data) {
  act(() => {tree = TestRenderer.create(<Ranking data={snapshot} viewProfile={() => {}} />)});
}
afterEach(() => {if (tree) act(() => tree.unmount())});
function field(label) {
  return tree.root.findAllByType('label').find(node =>
    node.findAllByType('span').some(span => span.children.join('') === label)).findByType('select');
}
function change(label, value) {act(() => field(label).props.onChange({target: {value}}))}
function names() {return tree.root.findByType('tbody').findAllByType('b').map(node => node.children.join(''))}

describe('Ranking filtering and calculations', () => {
  it('sorts by goals and searches names without accents', () => {
    mount();
    expect(names()).toEqual(['João', 'Martín', 'José']);
    act(() => tree.root.findByProps({'aria-label': 'Buscar'}).props.onChange({target: {value: 'joao'}}));
    expect(names()).toEqual(['João']);
  });
  it('combines club, position and minimum minutes', () => {
    mount();
    change('Clube', 'Alpha');
    change('Posição', 'W');
    expect(names()).toEqual(['João', 'José']);
    change('Mín. minutos', '900');
    expect(names()).toEqual(['João']);
  });
  it('converts totals by minutes and reorders the ranking', () => {
    mount();
    const toggle = tree.root.findAllByType('input').find(node => node.props.type === 'checkbox');
    act(() => toggle.props.onChange({target: {checked: true}}));
    expect(names()).toEqual(['João', 'José', 'Martín']);
    const values = tree.root.findAllByProps({className: 'metric-strong'}).map(node => node.children.join(''));
    expect(values).toEqual(['1', '0,8', '0,4']);
  });
  it('switches to club rankings without applying player filters', () => {
    mount();
    change('Clube', 'Alpha');
    change('Categoria', 'clubs');
    expect(names()).toEqual(['Beta', 'Alpha']);
  });
  it('resets pagination after a new search', () => {
    const snapshot = structuredClone(data);
    snapshot.players = Array.from({length: 30}, (_, i) => ({...data.players[0], id: String(i), name: `Atleta ${i}`, s: {'1': 30-i}}));
    mount(snapshot);
    expect(names()).toHaveLength(25);
    const next = tree.root.findAllByType('button').find(node => node.children.join('') === 'Próxima');
    act(() => next.props.onClick());
    expect(names()).toHaveLength(5);
    act(() => tree.root.findByProps({'aria-label': 'Buscar'}).props.onChange({target: {value: 'Atleta 0'}}));
    expect(names()).toEqual(['Atleta 0']);
  });
});
