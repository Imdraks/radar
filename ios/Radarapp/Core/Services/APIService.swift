// APIService.swift
// Main API service for Radarapp

import Foundation

// MARK: - API Error
enum APIError: Error, LocalizedError {
    case invalidURL
    case noData
    case decodingError
    case networkError(Error)
    case serverError(Int, String)
    case unauthorized
    
    var errorDescription: String? {
        switch self {
        case .invalidURL: return "URL invalide"
        case .noData: return "Aucune donnée reçue"
        case .decodingError: return "Erreur de décodage"
        case .networkError(let error): return error.localizedDescription
        case .serverError(let code, let message): return "Erreur \(code): \(message)"
        case .unauthorized: return "Non autorisé"
        }
    }
}

// MARK: - API Service
@MainActor
class APIService: ObservableObject {
    static let shared = APIService()
    
    private let baseURL: String
    private let session: URLSession
    private let decoder: JSONDecoder
    
    @Published var isLoading = false
    
    init() {
        self.baseURL = "https://radarapp.fr/api/v1"
        
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
        
        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase
    }
    
    // MARK: - Auth Header
    private var authHeaders: [String: String] {
        var headers = ["Content-Type": "application/json"]
        if let token = AuthService.shared.token {
            headers["Authorization"] = "Bearer \(token)"
        }
        return headers
    }
    
    // MARK: - Generic Request
    func request<T: Decodable>(
        endpoint: String,
        method: String = "GET",
        body: Data? = nil
    ) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.allHTTPHeaderFields = authHeaders
        request.httpBody = body
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.noData
        }
        
        if httpResponse.statusCode == 401 {
            await AuthService.shared.logout()
            throw APIError.unauthorized
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.serverError(httpResponse.statusCode, message)
        }
        
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            print("Decoding error: \(error)")
            throw APIError.decodingError
        }
    }
    
    // MARK: - Opportunities
    func fetchOpportunities(
        page: Int = 1,
        limit: Int = 20,
        search: String? = nil,
        status: String? = nil
    ) async throws -> PaginatedResponse<Opportunity> {
        var endpoint = "/opportunities?page=\(page)&limit=\(limit)"
        if let search = search, !search.isEmpty {
            endpoint += "&search=\(search.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? search)"
        }
        if let status = status {
            endpoint += "&status=\(status)"
        }
        return try await request(endpoint: endpoint)
    }
    
    func fetchOpportunity(id: Int) async throws -> Opportunity {
        return try await request(endpoint: "/opportunities/\(id)")
    }
    
    // MARK: - Dossiers
    func fetchDossiers(
        page: Int = 1,
        limit: Int = 20,
        status: String? = nil
    ) async throws -> PaginatedResponse<Dossier> {
        var endpoint = "/dossiers?page=\(page)&limit=\(limit)"
        if let status = status {
            endpoint += "&status=\(status)"
        }
        return try await request(endpoint: endpoint)
    }
    
    func fetchDossier(id: Int) async throws -> Dossier {
        return try await request(endpoint: "/dossiers/\(id)")
    }
    
    // MARK: - Sources
    func fetchSources() async throws -> [Source] {
        return try await request(endpoint: "/sources")
    }
    
    func createSource(_ source: CreateSourceRequest) async throws -> Source {
        let body = try JSONEncoder().encode(source)
        return try await request(endpoint: "/sources", method: "POST", body: body)
    }
    
    // MARK: - Artist Analysis
    func fetchArtistHistory() async throws -> [ArtistAnalysis] {
        return try await request(endpoint: "/artists/history")
    }
    
    func analyzeArtist(name: String) async throws -> ArtistAnalysis {
        let body = try JSONEncoder().encode(["name": name])
        return try await request(endpoint: "/artists/analyze", method: "POST", body: body)
    }
    
    // MARK: - Dashboard
    func fetchDashboard() async throws -> DashboardData {
        return try await request(endpoint: "/dashboard")
    }
}

// MARK: - Response Types
struct PaginatedResponse<T: Decodable>: Decodable {
    let items: [T]
    let total: Int
    let page: Int
    let pages: Int
}

struct CreateSourceRequest: Encodable {
    let name: String
    let type: String
    let url: String?
    let options: [String: String]?
}

struct DashboardData: Decodable {
    let totalOpportunities: Int
    let activeOpportunities: Int
    let totalDossiers: Int
    let pendingDossiers: Int
    let recentOpportunities: [Opportunity]
    let recentDossiers: [Dossier]
}
