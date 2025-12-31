// GlassComponents.swift
// Standard iOS 17 UI components

import SwiftUI

// MARK: - Card Style
enum CardStyle {
    case `default`
    case primary
    case success
    case warning
    case danger
    case elevated
    case card
    
    var backgroundColor: Color {
        switch self {
        case .default: return Color(.systemBackground)
        case .primary: return Color.blue.opacity(0.1)
        case .success: return Color.green.opacity(0.1)
        case .warning: return Color.orange.opacity(0.1)
        case .danger: return Color.red.opacity(0.1)
        case .elevated: return Color(.secondarySystemBackground)
        case .card: return Color(.tertiarySystemBackground)
        }
    }
    
    var borderColor: Color {
        switch self {
        case .default: return Color(.separator)
        case .primary: return Color.blue.opacity(0.3)
        case .success: return Color.green.opacity(0.3)
        case .warning: return Color.orange.opacity(0.3)
        case .danger: return Color.red.opacity(0.3)
        case .elevated: return Color(.separator)
        case .card: return Color(.separator).opacity(0.5)
        }
    }
}

// MARK: - Glass Background (simplified)
struct GlassBackground: View {
    let style: CardStyle
    let cornerRadius: CGFloat
    
    init(style: CardStyle = .default, cornerRadius: CGFloat = 12) {
        self.style = style
        self.cornerRadius = cornerRadius
    }
    
    var body: some View {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
            .fill(style.backgroundColor)
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(style.borderColor, lineWidth: 1)
            )
    }
}

// Backward compatibility alias
typealias GlassStyle = CardStyle

// MARK: - Glass Card
struct GlassCard<Content: View>: View {
    let style: CardStyle
    let padding: CGFloat
    let cornerRadius: CGFloat
    @ViewBuilder let content: Content
    
    init(style: CardStyle = .default, padding: CGFloat = 16, cornerRadius: CGFloat = 12, @ViewBuilder content: () -> Content) {
        self.style = style
        self.padding = padding
        self.cornerRadius = cornerRadius
        self.content = content()
    }
    
    var body: some View {
        content
            .padding(padding)
            .background(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(style.backgroundColor)
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(style.borderColor, lineWidth: 0.5)
            )
    }
}

// MARK: - Glass Button
struct GlassButton: View {
    let title: String
    let icon: String?
    let style: ButtonStyle
    let isLoading: Bool
    let action: () -> Void
    
    enum ButtonStyle {
        case primary
        case secondary
        case danger
        
        var backgroundColor: Color {
            switch self {
            case .primary: return .blue
            case .secondary: return Color(.secondarySystemBackground)
            case .danger: return .red
            }
        }
        
        var foregroundColor: Color {
            switch self {
            case .primary: return .white
            case .secondary: return .primary
            case .danger: return .white
            }
        }
    }
    
    init(
        _ title: String,
        icon: String? = nil,
        style: ButtonStyle = .primary,
        isLoading: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.style = style
        self.isLoading = isLoading
        self.action = action
    }
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: style.foregroundColor))
                        .scaleEffect(0.8)
                } else {
                    if let icon = icon {
                        Image(systemName: icon)
                    }
                    Text(title)
                        .fontWeight(.semibold)
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(style.backgroundColor)
            .foregroundColor(style.foregroundColor)
            .cornerRadius(10)
        }
        .disabled(isLoading)
    }
}

// MARK: - Glass TextField
struct GlassTextField: View {
    let placeholder: String
    @Binding var text: String
    let icon: String?
    let isSecure: Bool
    
    init(_ placeholder: String, text: Binding<String>, icon: String? = nil, isSecure: Bool = false) {
        self.placeholder = placeholder
        self._text = text
        self.icon = icon
        self.isSecure = isSecure
    }
    
    var body: some View {
        HStack(spacing: 12) {
            if let icon = icon {
                Image(systemName: icon)
                    .foregroundColor(.secondary)
                    .frame(width: 20)
            }
            
            if isSecure {
                SecureField(placeholder, text: $text)
            } else {
                TextField(placeholder, text: $text)
            }
        }
        .padding()
        .background(Color(.secondarySystemBackground))
        .cornerRadius(10)
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color(.separator), lineWidth: 0.5)
        )
    }
}

// MARK: - Score Badge
struct ScoreBadge: View {
    let score: Int
    
    private var color: Color {
        switch score {
        case 80...100: return .green
        case 60..<80: return .blue
        case 40..<60: return .orange
        default: return .red
        }
    }
    
    var body: some View {
        Text("\(score)")
            .font(.system(.caption, design: .rounded, weight: .bold))
            .foregroundColor(.white)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color)
            .cornerRadius(12)
    }
}

// MARK: - Status Badge
struct StatusBadge: View {
    let status: String
    let color: Color
    
    init(_ status: String, color: Color = .blue) {
        self.status = status
        self.color = color
    }
    
    var body: some View {
        Text(status)
            .font(.caption)
            .fontWeight(.medium)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color.opacity(0.15))
            .cornerRadius(8)
    }
}

// MARK: - Loading View
struct LoadingView: View {
    let message: String
    
    init(_ message: String = "Chargement...") {
        self.message = message
    }
    
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Empty State View
struct EmptyStateView: View {
    let icon: String
    let title: String
    let message: String
    let actionTitle: String?
    let action: (() -> Void)?
    
    init(
        icon: String,
        title: String,
        message: String,
        actionTitle: String? = nil,
        action: (() -> Void)? = nil
    ) {
        self.icon = icon
        self.title = title
        self.message = message
        self.actionTitle = actionTitle
        self.action = action
    }
    
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(.secondary)
            
            Text(title)
                .font(.title3)
                .fontWeight(.semibold)
            
            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            
            if let actionTitle = actionTitle, let action = action {
                Button(action: action) {
                    Text(actionTitle)
                        .fontWeight(.medium)
                }
                .buttonStyle(.borderedProminent)
                .padding(.top, 8)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

// MARK: - Section Header
struct SectionHeader: View {
    let title: String
    let icon: String?
    
    init(_ title: String, icon: String? = nil) {
        self.title = title
        self.icon = icon
    }
    
    var body: some View {
        HStack(spacing: 8) {
            if let icon = icon {
                Image(systemName: icon)
                    .foregroundColor(.blue)
            }
            Text(title)
                .font(.headline)
            Spacer()
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
    }
}

// MARK: - Info Row
struct InfoRow: View {
    let label: String
    let value: String
    let icon: String?
    
    init(_ label: String, value: String, icon: String? = nil) {
        self.label = label
        self.value = value
        self.icon = icon
    }
    
    var body: some View {
        HStack {
            if let icon = icon {
                Image(systemName: icon)
                    .foregroundColor(.secondary)
                    .frame(width: 24)
            }
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
        }
    }
}
