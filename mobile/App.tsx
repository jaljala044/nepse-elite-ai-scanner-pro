import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View, useColorScheme } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

const tabs = ['Home', 'Scan', 'Portfolio', 'More'] as const;
type Tab = typeof tabs[number];
const screens: Record<Tab, { title: string; rows: string[] }> = {
  Home: { title: 'Market overview', rows: ['NEPSE index', 'Market health', 'Sector rotation', 'Broker activity'] },
  Scan: { title: 'Research scanners', rows: ['IDPAT', 'Wyckoff', 'SMC', 'Broker Footprint', 'Minervini Momentum', 'Master Hybrid'] },
  Portfolio: { title: 'Portfolio intelligence', rows: ['Holdings', 'Risk protection', 'Entry and exit plans', 'T+2 settlement'] },
  More: { title: 'Research tools', rows: ['Watchlists', 'Alerts', 'Relative rotation', 'Point & Figure'] },
};

function Shell() {
  const [tab, setTab] = useState<Tab>('Home');
  const dark = useColorScheme() === 'dark';
  const colors = dark
    ? { bg: '#10151f', card: '#1e2938', text: '#f1f5f9', muted: '#b6c3d2', accent: '#66d9a5' }
    : { bg: '#f4f6fa', card: '#ffffff', text: '#162234', muted: '#526277', accent: '#08734c' };
  return (
    <SafeAreaView style={[styles.root, { backgroundColor: colors.bg }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={[styles.brand, { color: colors.accent }]}>NEPSE ELITE AI</Text>
        <Text accessibilityRole="header" style={[styles.title, { color: colors.text }]}>{screens[tab].title}</Text>
        <Text style={{ color: colors.muted }}>Research preview • Data connection not configured</Text>
        {screens[tab].rows.map(label => (
          <View key={label} style={[styles.card, { backgroundColor: colors.card }]}>
            <Text style={[styles.label, { color: colors.text }]}>{label}</Text>
            <Text style={{ color: colors.muted }}>Unavailable — not connected</Text>
          </View>
        ))}
        <Text style={{ color: colors.muted }}>No live recommendations, execution or stored personal holdings.</Text>
      </ScrollView>
      <View style={[styles.nav, { backgroundColor: colors.card }]}>
        {tabs.map(item => (
          <Pressable key={item} accessibilityRole="tab" accessibilityState={{ selected: tab === item }}
            onPress={() => setTab(item)} style={styles.tab}>
            <Text style={{ color: tab === item ? colors.accent : colors.muted, fontWeight: tab === item ? '700' : '400' }}>{item}</Text>
          </Pressable>
        ))}
      </View>
    </SafeAreaView>
  );
}
export default function App() {
  return <SafeAreaProvider><Shell /></SafeAreaProvider>;
}
const styles = StyleSheet.create({
  root: { flex: 1 }, content: { padding: 20, gap: 14 },
  brand: { fontSize: 12, fontWeight: '700', letterSpacing: 1.2 },
  title: { fontSize: 28, fontWeight: '700' },
  card: { padding: 16, borderRadius: 14, gap: 6 }, label: { fontSize: 17, fontWeight: '600' },
  nav: { flexDirection: 'row', paddingHorizontal: 8 },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 56 },
});
