import { Component, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface SearchFilters {
  query: string;
  status?: string;
  level?: string;
  dateFrom?: Date;
  dateTo?: Date;
  sortBy?: string;
}

@Component({
  selector: 'app-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="search-container">
      <div class="search-bar">
        <span class="search-icon">🔍</span>
        <input
          type="text"
          [(ngModel)]="filters.query"
          (ngModelChange)="onSearch()"
          placeholder="Rechercher un mémoire..."
          class="search-input"
        />
        <button class="filter-toggle" (click)="showFilters = !showFilters" title="Filtres">
          ⚙️
        </button>
        <button *ngIf="filters.query" class="clear-btn" (click)="clearQuery()">✕</button>
      </div>

      <div *ngIf="showFilters" class="filters-panel">
        <div class="filter-row">
          <div class="filter-group">
            <label>Statut</label>
            <select [(ngModel)]="filters.status" (change)="onSearch()">
              <option value="">Tous</option>
              <option value="draft">Brouillon</option>
              <option value="in_progress">En cours</option>
              <option value="review">En révision</option>
              <option value="completed">Terminé</option>
            </select>
          </div>

          <div class="filter-group">
            <label>Niveau</label>
            <select [(ngModel)]="filters.level" (change)="onSearch()">
              <option value="">Tous</option>
              <option value="LICENCE">Licence</option>
              <option value="MASTER">Master</option>
              <option value="DOCTORAT">Doctorat</option>
            </select>
          </div>
        </div>

        <div class="filter-row">
          <div class="filter-group">
            <label>Date de</label>
            <input type="date" [(ngModel)]="filters.dateFrom" (change)="onSearch()" />
          </div>

          <div class="filter-group">
            <label>Date à</label>
            <input type="date" [(ngModel)]="filters.dateTo" (change)="onSearch()" />
          </div>

          <div class="filter-group">
            <label>Trier par</label>
            <select [(ngModel)]="filters.sortBy" (change)="onSearch()">
              <option value="date">Date récente</option>
              <option value="title">Titre</option>
              <option value="status">Statut</option>
            </select>
          </div>
        </div>

        <div class="filter-actions">
          <button class="btn-clear" (click)="clearFilters()">🗑️ Effacer les filtres</button>
          <span class="filter-count" *ngIf="hasActiveFilters()">
            {{ getActiveFilterCount() }} filtre(s) actif(s)
          </span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .search-container {
      margin-bottom: 20px;
    }

    .search-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--bg-card, #ffffff);
      border: 2px solid var(--border-color, #e5eceb);
      border-radius: 12px;
      padding: 4px 14px;
      transition: all 0.3s ease;
    }

    .search-bar:focus-within {
      border-color: #0f766e;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }

    .search-icon {
      font-size: 16px;
      color: var(--text-muted, #748482);
    }

    .search-input {
      flex: 1;
      padding: 12px 0;
      border: none;
      background: transparent;
      font-size: 14px;
      color: var(--text-primary, #173e3a);
      outline: none;
    }

    .search-input::placeholder {
      color: var(--text-muted, #748482);
    }

    .filter-toggle {
      background: none;
      border: none;
      padding: 8px;
      cursor: pointer;
      font-size: 18px;
      color: var(--text-muted, #748482);
      border-radius: 8px;
      transition: all 0.2s;
    }

    .filter-toggle:hover {
      background: var(--bg-hover, #f0f5f4);
      color: var(--text-primary, #173e3a);
    }

    .clear-btn {
      background: none;
      border: none;
      color: var(--text-muted, #748482);
      cursor: pointer;
      font-size: 14px;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.2s;
    }

    .clear-btn:hover {
      background: #fee2e2;
      color: #991b1b;
    }

    .filters-panel {
      margin-top: 12px;
      padding: 16px 20px;
      background: var(--bg-card, #ffffff);
      border: 1px solid var(--border-color, #e5eceb);
      border-radius: 12px;
      animation: slideDown 0.3s ease;
    }

    .filter-row {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 15px;
      margin-bottom: 12px;
    }

    .filter-row:last-child {
      margin-bottom: 0;
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .filter-group label {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted, #748482);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .filter-group select,
    .filter-group input {
      padding: 8px 12px;
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      background: var(--bg-input, #fbfdfd);
      color: var(--text-primary, #173e3a);
      font-size: 13px;
      outline: none;
      transition: all 0.2s;
    }

    .filter-group select:focus,
    .filter-group input:focus {
      border-color: #0f766e;
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }

    .filter-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--border-color, #e5eceb);
    }

    .btn-clear {
      padding: 6px 16px;
      background: none;
      border: 1px solid var(--border-color, #dce7e5);
      border-radius: 8px;
      color: var(--text-muted, #748482);
      cursor: pointer;
      font-size: 12px;
      transition: all 0.2s;
    }

    .btn-clear:hover {
      border-color: #be123c;
      color: #be123c;
      background: #fff1f2;
    }

    .filter-count {
      font-size: 12px;
      color: #0f766e;
      font-weight: 500;
    }

    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 768px) {
      .filter-row {
        grid-template-columns: 1fr 1fr;
      }
    }

    @media (max-width: 480px) {
      .filter-row {
        grid-template-columns: 1fr;
      }

      .filter-actions {
        flex-direction: column;
        gap: 8px;
        align-items: stretch;
      }

      .filter-count {
        text-align: center;
      }
    }
  `]
})
export class SearchComponent implements OnInit {
  @Output() search = new EventEmitter<SearchFilters>();

  showFilters = false;
  filters: SearchFilters = {
    query: '',
    status: '',
    level: '',
    dateFrom: undefined,
    dateTo: undefined,
    sortBy: 'date'
  };

  ngOnInit(): void {
    // Initialisation
  }

  onSearch(): void {
    this.search.emit({ ...this.filters });
  }

  clearQuery(): void {
    this.filters.query = '';
    this.onSearch();
  }

  clearFilters(): void {
    this.filters = {
      query: '',
      status: '',
      level: '',
      dateFrom: undefined,
      dateTo: undefined,
      sortBy: 'date'
    };
    this.onSearch();
  }

  hasActiveFilters(): boolean {
    return !!(
      this.filters.status ||
      this.filters.level ||
      this.filters.dateFrom ||
      this.filters.dateTo
    );
  }

  getActiveFilterCount(): number {
    let count = 0;
    if (this.filters.status) count++;
    if (this.filters.level) count++;
    if (this.filters.dateFrom) count++;
    if (this.filters.dateTo) count++;
    return count;
  }
}